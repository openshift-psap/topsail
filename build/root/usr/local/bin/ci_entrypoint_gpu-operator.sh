#! /usr/bin/env bash

set -o pipefail
set -o errexit
set -o nounset

prepare_cluster_for_gpu_operator() {
    ./run_toolbox.py cluster capture_environment

    finalizers+=("collect_must_gather")
    finalizers+=("./run_toolbox.py entitlement undeploy &> /dev/null")

    entitle.sh

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
        (cat "$ARTIFACT_EXTRA_LOGS_DIR"/*__cluster__capture_environment/ocp.version || echo MISSING) > ${ARTIFACT_DIR}/ocp.version
        (cat "$ARTIFACT_EXTRA_LOGS_DIR"/*__cluster__capture_environment/ci_artifact.git_version || echo MISSING) > ${ARTIFACT_DIR}/ci_artifact.git_version

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
    ./run_toolbox.py nfd-operator undeploy_from_operatorhub

    # ensure that the MachineConfigPool have finished all pending updates
    tries_left=20
    WAIT_TIME_SECONDS=30

    MCP_MACHINE_COUNT=$(oc get mcp -ojsonpath={.items[*].status.machineCount} | jq .)
    while true; do
        mcp_machine_updated=$(oc get mcp -ojsonpath={.items[*].status.updatedMachineCount} | jq .)
        if [ "$MCP_MACHINE_COUNT" == "$mcp_machine_updated" ]; then
            echo "All the MachineConfigPools have been updated."
            break
        fi
        tries_left=$(($tries_left - 1))
        if [[ $tries_left == 0 ]]; then
            cat <<EOF
Failed to wait for the MachineConfigPools to be properly updated.
machineCount:
$MCP_MACHINE_COUNT

updatedMachineCount:
$mcp_machine_updated
EOF
            exit 1
        fi
        sleep $WAIT_TIME_SECONDS
    done
}

test_master_branch() {
    prepare_cluster_for_gpu_operator
    ./run_toolbox.py gpu_operator deploy_from_bundle --bundle=master

    validate_gpu_operator_deployment --bundle=master
}

test_commit() {
    gpu_operator_git_repo="${1:-}"
    gpu_operator_git_ref="${2:-}"
    CI_IMAGE_GPU_COMMIT_CI_IMAGE_UID="ci-image"

    if [[ -z "$gpu_operator_git_repo" || -z "$gpu_operator_git_ref" ]]; then
        echo "FATAL: test_commit must receive a git repo/ref to be tested."
        return 1
    fi

    echo "Using Git repository ${gpu_operator_git_repo} with ref ${gpu_operator_git_ref}"

    prepare_cluster_for_gpu_operator

    GPU_OPERATOR_QUAY_BUNDLE_PUSH_SECRET=${GPU_OPERATOR_QUAY_BUNDLE_PUSH_SECRET:-"/var/run/psap-entitlement-secret/openshift-psap-openshift-ci-secret.yml"}
    GPU_OPERATOR_QUAY_BUNDLE_IMAGE_NAME=${GPU_OPERATOR_QUAY_BUNDLE_IMAGE_NAME:-"quay.io/openshift-psap/ci-artifacts"}

    ./run_toolbox.py gpu_operator bundle_from_commit "${gpu_operator_git_repo}" \
                                             "${gpu_operator_git_ref}" \
                                             "${GPU_OPERATOR_QUAY_BUNDLE_PUSH_SECRET}" \
                                             "${GPU_OPERATOR_QUAY_BUNDLE_IMAGE_NAME}" \
                                             --tag_uid="${CI_IMAGE_GPU_COMMIT_CI_IMAGE_UID}"

    ./run_toolbox.py gpu_operator deploy_from_bundle "--bundle=${GPU_OPERATOR_QUAY_BUNDLE_IMAGE_NAME}:operator_bundle_gpu-operator-ci-image"

    validate_gpu_operator_deployment
}

test_operatorhub() {
    if [ "${1:-}" ]; then
        OPERATOR_VERSION="--version=$1"
    fi
    shift || true
    if [ "${1:-}" ]; then
        OPERATOR_CHANNEL="--channel=$1"
    fi

    prepare_cluster_for_gpu_operator
    ./run_toolbox.py gpu_operator deploy_from_operatorhub ${OPERATOR_VERSION:-} ${OPERATOR_CHANNEL:-}
    validate_gpu_operator_deployment
}

test_helm() {
    if [ -z "${1:-}" ]; then
        echo "FATAL: run $0 should receive the operator version as parameter."
        exit 1
    fi
    OPERATOR_VERSION="$1"

    prepare_cluster_for_gpu_operator
    toolbox/gpu-operator/list_version_from_helm.sh
    toolbox/gpu-operator/deploy_with_helm.sh ${OPERATOR_VERSION}
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
        ## currently broken
        #test_master_branch "$@"
        test_commit "https://github.com/NVIDIA/gpu-operator.git" master
        exit 0
        ;;
    "test_commit")
        test_commit "https://github.com/NVIDIA/gpu-operator.git" master
        exit 0
        ;;
    "test_operatorhub")
        test_operatorhub "$@"
        exit 0
        ;;
    "validate_deployment")
        validate_gpu_operator_deployment "$@"
        exit 0
        ;;
    "test_helm")
        test_helm "$@"
        exit 0
        ;;
    "undeploy_operatorhub" | "cleanup_cluster")
        cleanup_cluster
        exit 0
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
