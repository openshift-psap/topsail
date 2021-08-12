#! /usr/bin/env bash

set -o pipefail
set -o errexit
set -o nounset

THIS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd ${THIS_DIR}/../..

prepare_cluster_for_gpu_operator() {
    ./run_toolbox.py cluster capture_environment

    finalizers+=("collect_must_gather")

    if [[ "${1:-}" != "no_undeploy" ]]; then
        finalizers+=("./run_toolbox.py entitlement undeploy &> /dev/null")
    fi

    ${THIS_DIR}/entitle.sh

    if ! ./run_toolbox.py nfd has_labels; then
        ./run_toolbox.py nfd_operator deploy_from_operatorhub
    fi

    if ! ./run_toolbox.py nfd has_gpu_nodes; then
        ./run_toolbox.py cluster set_scale g4dn.xlarge 1
        ./run_toolbox.py nfd wait_gpu_nodes
    fi
}

collect_must_gather() {
    run_in_sub_shell() {
        echo "Running gpu-operator_gather ..."
        /usr/bin/gpu-operator_gather &> /dev/null

        # extract ARTIFACT_EXTRA_LOGS_DIR from 'source toolbox/_common.sh' without sourcing it directly

        export TOOLBOX_SCRIPT_NAME=toolbox/gpu-operator/must-gather.sh
        COMMON_SH=$(
            bash -c 'source toolbox/_common.sh;
                     echo "8<--8<--8<--";
                     # only evaluate these variables from _common.sh
                     env | egrep "(^ARTIFACT_EXTRA_LOGS_DIR=)"'
                 )
        ENV=$(echo "$COMMON_SH" | tac | sed '/8<--8<--8<--/Q' | tac) # keep only what's after the 8<--
        eval $ENV

        echo "Running gpu-operator_gather ... copying results to $ARTIFACT_EXTRA_LOGS_DIR"

        cp -r /must-gather/* "$ARTIFACT_EXTRA_LOGS_DIR"

        echo "Running gpu-operator_gather ... finished."

        (cat "$ARTIFACT_EXTRA_LOGS_DIR"/*__gpu_operator__get_csv_version/gpu_operator.version || echo MISSING) > ${ARTIFACT_DIR}/operator.version

        echo "Versions collected."
    }

    # run the function above in a subshell to avoid polluting the local `env`.
    typeset -fx run_in_sub_shell
    bash -c run_in_sub_shell
}

validate_gpu_operator_deployment() {
    ./run_toolbox.py gpu_operator wait_deployment
    ./run_toolbox.py gpu_operator run_gpu_burn
}

cleanup_cluster() {
    # undeploy the entitlement
    ./run_toolbox.py entitlement undeploy
    # ensure that there is no GPU Operator in the cluster
    ./run_toolbox.py gpu_operator undeploy_from_operatorhub
    # ensure that there is no GPU node in the cluster
    ./run_toolbox.py cluster set_scale g4dn.xlarge 0

    # ensure that NFD is not installed in the cluster
    ## not working as expected at the moment: NFD labels remain
    ## visible, but new labels not added, making the
    ## `nfd__wait_gpu_nodes` test fail.
    #./run_toolbox.py nfd-operator undeploy_from_operatorhub

    # ensure that the MachineConfigPool have finished all pending updates
    tries_left=40
    WAIT_TIME_SECONDS=30
    set -x

    while true; do
        mcp_machine_count=$(oc get mcp -ojsonpath={.items[*].status.machineCount} | jq .)
        mcp_machine_updated=$(oc get mcp -ojsonpath={.items[*].status.updatedMachineCount} | jq .)
        if [ "$mcp_machine_count" == "$mcp_machine_updated" ]; then
            echo "All the MachineConfigPools have been updated."
            break
        fi
        tries_left=$(($tries_left - 1))
        if [[ $tries_left == 0 ]]; then
            cat <<EOF
Failed to wait for the MachineConfigPools to be properly updated.
machineCount:
$mcp_machine_count

updatedMachineCount:
$mcp_machine_updated
EOF
            oc get mcp > ${ARTIFACT_DIR}/mcp.list
            oc describe mcp > ${ARTIFACT_DIR}/mcp.all.descr
            exit 1
        fi
        sleep $WAIT_TIME_SECONDS
    done
}

test_master_branch() {
    trap collect_must_gather EXIT

    oc label ns/openshift-operators openshift.io/cluster-monitoring=true --overwrite

    # currently broken, until we can generate in quay.io (or
    # elsewhere) a bundle image pointing to the the current master
    # operator image
    #./run_toolbox.py gpu_operator deploy_from_bundle --bundle=master

    # meanwhile:
    deploy_commit "https://github.com/NVIDIA/gpu-operator.git" "master"

    prepare_cluster_for_gpu_operator_with_alerts "$@"

    validate_gpu_operator_deployment
}

test_commit() {
    gpu_operator_git_repo="${1}"
    shift;
    gpu_operator_git_ref="${1}"
    shift;

    prepare_cluster_for_gpu_operator "$@"

    deploy_commit $gpu_operator_git_repo $gpu_operator_git_ref

    validate_gpu_operator_deployment
}

deploy_commit() {
    gpu_operator_git_repo="${1:-}"
    shift
    gpu_operator_git_ref="${1:-}"

    CI_IMAGE_GPU_COMMIT_CI_IMAGE_UID="ci-image"
    OPERATOR_NAMESPACE="nvidia-gpu-operator"

    if [[ -z "$gpu_operator_git_repo" || -z "$gpu_operator_git_ref" ]]; then
        echo "FATAL: test_commit must receive a git repo/ref to be tested."
        return 1
    fi

    echo "Using Git repository ${gpu_operator_git_repo} with ref ${gpu_operator_git_ref}"

    GPU_OPERATOR_QUAY_BUNDLE_PUSH_SECRET=${GPU_OPERATOR_QUAY_BUNDLE_PUSH_SECRET:-"/var/run/psap-entitlement-secret/openshift-psap-openshift-ci-secret.yml"}
    GPU_OPERATOR_QUAY_BUNDLE_IMAGE_NAME=${GPU_OPERATOR_QUAY_BUNDLE_IMAGE_NAME:-"quay.io/openshift-psap/ci-artifacts"}

    ./run_toolbox.py gpu_operator bundle_from_commit "${gpu_operator_git_repo}" \
                                             "${gpu_operator_git_ref}" \
                                             "${GPU_OPERATOR_QUAY_BUNDLE_PUSH_SECRET}" \
                                             "${GPU_OPERATOR_QUAY_BUNDLE_IMAGE_NAME}" \
                                             --tag_uid "${CI_IMAGE_GPU_COMMIT_CI_IMAGE_UID}" \
                                             --namespace "${OPERATOR_NAMESPACE}"

    ./run_toolbox.py gpu_operator deploy_from_bundle --bundle "${GPU_OPERATOR_QUAY_BUNDLE_IMAGE_NAME}:operator_bundle_gpu-operator-ci-image" \
                                                     --namespace "${OPERATOR_NAMESPACE}"
}

prepare_cluster_for_gpu_operator_with_alerts() {
    ./run_toolbox.py cluster capture_environment

    finalizers+=("collect_must_gather")

    if [[ "${1:-}" != "no_undeploy" ]]; then
        finalizers+=("./run_toolbox.py entitlement undeploy &> /dev/null")
    fi

    mkdir -p ${ARTIFACT_DIR}/alerts

    ./run_toolbox.py gpu-operator prepare_test_alerts \
                     --alert_delay=1 \
                     --alert_prefix=CI

    mv ${ARTIFACT_DIR}/*__gpu-operator__prepare_test_alerts ${ARTIFACT_DIR}/alerts

    # wait for NFD alert to fire
    if ! ./run_toolbox.py nfd has_labels; then
        ./run_toolbox.py cluster wait_for_alert \
                         CIGPUOperatorReconciliationFailedNfdLabelsMissing \
                         --alert-active=true
    else
        DEST_DIR="${ARTIFACT_DIR}/999__cluster__wait_for_alert__FailedNfdLabelsMissing"
        mkdir "$DEST_DIR"
        echo "Cannot check for NFD alert, nodes already labelled." > "$DEST_DIR/msg"
    fi

    mv ${ARTIFACT_DIR}/*__cluster__wait_for_alert* ${ARTIFACT_DIR}/alerts

    ./run_toolbox.py nfd_operator deploy_from_operatorhub
    ./run_toolbox.py cluster set_scale g4dn.xlarge 1

    # wait for NFD alert to stop firing
    ./run_toolbox.py cluster wait_for_alert \
                     CIGPUOperatorReconciliationFailedNfdLabelsMissing \
                     --alert-active=false
    if ! ./run_toolbox.py entitlement test_cluster --no_inspect; then
        # wait for driver alert to fire
        ./run_toolbox.py cluster wait_for_alert \
                         CIGPUOperatorNodeDeploymentDriverFailed \
                         --alert-active=true
    else
        DEST_DIR="${ARTIFACT_DIR}/999__cluster__wait_for_alert__NodeDeploymentDriverFailed__not_tested"
        mkdir "$DEST_DIR"
        echo "Cannot check for driver alert to fire, cluster already entitled." > "$DEST_DIR/msg"
    fi

    mv ${ARTIFACT_DIR}/*__cluster__wait_for_alert ${ARTIFACT_DIR}/alerts

    # entitle the cluster
    ${THIS_DIR}/entitle.sh

    # wait for driver alert to stop fireing
    ./run_toolbox.py cluster wait_for_alert \
                     CIGPUOperatorNodeDeploymentDriverFailed \
                     --alert-active=false
    mv ${ARTIFACT_DIR}/*__cluster__wait_for_alert ${ARTIFACT_DIR}/alerts
}

test_operatorhub() {
    if [ "${1:-}" ]; then
        OPERATOR_VERSION="--version=$1"
    fi
    shift || true
    if [ "${1:-}" ]; then
        OPERATOR_CHANNEL="--channel=$1"
    fi
    shift || true

    prepare_cluster_for_gpu_operator "$@"

    ./run_toolbox.py gpu_operator deploy_from_operatorhub ${OPERATOR_VERSION:-} ${OPERATOR_CHANNEL:-} --namespace openshift-operators
    validate_gpu_operator_deployment
}

validate_deployment_post_upgrade() {
    finalizers+=("collect_must_gather")
    finalizers+=("./run_toolbox.py entitlement undeploy &> /dev/null")

    ${THIS_DIR}/entitle.sh

    validate_gpu_operator_deployment
}

finalizers=()
run_finalizers() {
    [ ${#finalizers[@]} -eq 0 ] && return
    set +x

    echo "Running exit finalizers ..."
    for finalizer in "${finalizers[@]}"
    do
        echo "Running finalizer '$finalizer' ..."
        eval $finalizer
    done
}

if [ -z "${1:-}" ]; then
    echo "FATAL: $0 expects at least 1 argument ..."
    exit 1
fi

trap run_finalizers EXIT

action="$1"
shift

set -x

case ${action} in
    "test_master_branch")
        test_master_branch "$@"
        exit 0
        ;;
    "test_commit")
        test_commit "https://github.com/NVIDIA/gpu-operator.git" master "$@"
        exit 0
        ;;
    "test_operatorhub")
        test_operatorhub "$@"
        exit 0
        ;;
    "validate_deployment_post_upgrade")
        validate_gpu_operator_deployment
        exit 0
        ;;
    "cleanup_cluster")
        cleanup_cluster
        exit 0
        ;;
    "source")
        set +x
        echo "INFO: GPU Operator CI entrypoint has been sourced"
        # file is being sourced by another script
        ;;
    -*)
        echo "FATAL: Unknown option: ${action}"
        exit 1
        ;;
    *)
        echo "FATAL: Nothing to do ..."
        exit 1
        ;;
esac
