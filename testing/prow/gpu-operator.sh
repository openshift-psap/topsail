#! /usr/bin/env bash

set -o pipefail
set -o errexit
set -o nounset

THIS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd ${THIS_DIR}/../..

_warning() {
    fname="$1"
    msg="$2"

    DEST_DIR="${ARTIFACT_DIR}/_WARNING/"
    mkdir -p "$DEST_DIR"
    echo "$msg" > "${DEST_DIR}/$fname"

    echo "WARNING: $msg"
}

_expected_fail() {
    # mark the last toolbox step as an expected fail (for clearer
    # parsing/display in ci-dashboard)
    # eg: if cluster doesn't have NFD labels (expected fail), deploy NFD
    # eg: if cluster doesn't have GPU nodes (expected fail), scale up with GPU nodes

    last_toolbox_dir=$(ls ${ARTIFACT_DIR}/*__* -d | tail -1)
    echo "$1" > ${last_toolbox_dir}/EXPECTED_FAIL
}

DTK_NOT_VALID_WARNING_FLAG=dtk_image_not_valid
dtk_image_is_valid() {
    if [[ -f ${ARTIFACT_DIR}/_WARNING/$DTK_NOT_VALID_WARNING_FLAG ]]; then
        echo "Found 'dtk_image_not_valid' warning flag"
        return 1
    fi

    MINI_POD_SPEC='{"apiVersion": "v1", "kind":"Pod","metadata":{"name":"test"},"spec":{"containers":[{"name":"cnt"}]}}'
    DTK_IMAGE="image-registry.openshift-image-registry.svc:5000/openshift/driver-toolkit:latest"

    dtk_release=$(oc debug --quiet -f <(echo "$MINI_POD_SPEC") --image=${DTK_IMAGE} \
                     -- \
                     cat /etc/driver-toolkit-release.json)
    dtk_kernel=$(echo "$dtk_release" | jq -r .KERNEL_VERSION)

    node_kernel=$(oc get nodes -ojsonpath={.items[].status.nodeInfo.kernelVersion})

    echo "Driver toolkit 'latest' image kernel: ${dtk_kernel}"
    echo "Nodes kernel: ${node_kernel}"

    [[ "${dtk_kernel}" == "${node_kernel}" ]]
}

dtk_or_entitle() {
    if dtk_image_is_valid; then
        echo "DTK image is valid"
    else
        # During OpenShift nightly testing, the DTK image may be
        # invalid, when the release-controller updated the RHCOS
        # version but didn't trigger a Driver Toolkit rebuild. This is
        # expected, and should not impact publicly released OpenShift
        # versions.

        _warning $DTK_NOT_VALID_WARNING_FLAG "Driver Toolkit image is not valid, using entitled-build fallback"
        ${THIS_DIR}/entitle.sh
    fi

}

prepare_cluster_for_gpu_operator() {
    ./run_toolbox.py cluster capture_environment

    finalizers+=("collect_must_gather")

    if [[ "${1:-}" != "no_undeploy" ]]; then
        finalizers+=("./run_toolbox.py entitlement undeploy &> /dev/null")
    fi

    ${THIS_DIR}/entitle.sh

    if ! ./run_toolbox.py nfd has_labels; then
        _expected_fail "Checking if the cluster had NFD labels"

        if oc get packagemanifests/nfd -n openshift-marketplace > /dev/null; then
            ./run_toolbox.py nfd_operator deploy_from_operatorhub
        else
            # in 4.9, NFD is currently not available from its default location,
            _warning "NFD_deployed_from_master" "NFD was deployed from master (not available in OperatorHub)"

            # install the NFD Operator from sources
            CI_IMAGE_NFD_COMMIT_CI_REPO="${1:-https://github.com/openshift/cluster-nfd-operator.git}"
            CI_IMAGE_NFD_COMMIT_CI_REF="${2:-master}"
            CI_IMAGE_NFD_COMMIT_CI_IMAGE_TAG="ci-image"
            ./run_toolbox.py nfd_operator deploy_from_commit "${CI_IMAGE_NFD_COMMIT_CI_REPO}" \
                             "${CI_IMAGE_NFD_COMMIT_CI_REF}"  \
                             --image-tag="${CI_IMAGE_NFD_COMMIT_CI_IMAGE_TAG}"
        fi
    fi

    if ! ./run_toolbox.py nfd has_gpu_nodes; then
        _expected_fail "Checking if the cluster had GPU nodes"

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
    if ! dtk_image_is_valid; then
        oc patch clusterpolicy/gpu-cluster-policy --type='json' -p='[{"op": "replace", "path": "/spec/driver/use_ocp_driver_toolkit", "value": false}]' # noop if ClusterPolicy field doesn't exist
    fi

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
    deploy_commit "https://gitlab.com/nvidia/kubernetes/gpu-operator.git" "master"

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
                                             --namespace "${OPERATOR_NAMESPACE}" \
                                             --with_validator=true \
                                             --publish_to_quay=true

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
        _expected_fail "Checking if the cluster had NFD labels"

        ./run_toolbox.py cluster wait_for_alert \
                         CIGPUOperatorReconciliationFailedNfdLabelsMissing \
                         --alert-active=true
    else
        DEST_DIR="${ARTIFACT_DIR}/999__cluster__wait_for_alert__FailedNfdLabelsMissing"
        mkdir "$DEST_DIR"
        echo "Cannot check for NFD alert, nodes already labelled." > "$DEST_DIR/msg"
    fi

    mv ${ARTIFACT_DIR}/*__cluster__wait_for_alert* ${ARTIFACT_DIR}/alerts

    if ! ./run_toolbox.py nfd has_labels; then
        _expected_fail "Checking if the cluster had NFD labels"

        if oc get packagemanifests/nfd -n openshift-marketplace > /dev/null; then
            ./run_toolbox.py nfd_operator deploy_from_operatorhub
        else
            # in 4.9, NFD is currently not available from its default location,
            _warning "NFD_deployed_from_master" "NFD was deployed from master (not available in OperatorHub)"
            # install the NFD Operator from sources
            CI_IMAGE_NFD_COMMIT_CI_REPO="${1:-https://github.com/openshift/cluster-nfd-operator.git}"
            CI_IMAGE_NFD_COMMIT_CI_REF="${2:-master}"
            CI_IMAGE_NFD_COMMIT_CI_IMAGE_TAG="ci-image"
            ./run_toolbox.py nfd_operator deploy_from_commit "${CI_IMAGE_NFD_COMMIT_CI_REPO}" \
                             "${CI_IMAGE_NFD_COMMIT_CI_REF}"  \
                             --image-tag="${CI_IMAGE_NFD_COMMIT_CI_IMAGE_TAG}"
        fi
    fi
    if ! ./run_toolbox.py nfd has_gpu_nodes; then
        _expected_fail "Checking if the cluster had GPU nodes"

        ./run_toolbox.py cluster set_scale g4dn.xlarge 1
        ./run_toolbox.py nfd wait_gpu_nodes
    fi

    # wait for NFD alert to stop firing
    ./run_toolbox.py cluster wait_for_alert \
                     CIGPUOperatorReconciliationFailedNfdLabelsMissing \
                     --alert-active=false
    if ! ./run_toolbox.py entitlement test_cluster --no_inspect; then
        _expected_fail "Checking if the cluster was entitled"

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

    dtk_or_entitle

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

    dtk_or_entitle

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
        test_commit "https://gitlab.com/nvidia/kubernetes/gpu-operator.git" master "$@"
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
