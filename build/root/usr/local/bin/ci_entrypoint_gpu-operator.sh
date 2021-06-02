#! /usr/bin/env bash

set -o pipefail
set -o errexit
set -o nounset

prepare_cluster_for_gpu_operator() {
    trap collect_must_gather ERR

    toolbox/cluster/capture_environment.sh
    entitle.sh

    if ! toolbox/nfd/has_nfd_labels.sh; then
        toolbox/nfd-operator/deploy_from_operatorhub.sh
    fi

    if ! toolbox/nfd/has_gpu_nodes.sh; then
        toolbox/cluster/set_scale.sh g4dn.xlarge 1
        toolbox/nfd/wait_gpu_nodes.sh
    fi
}

collect_must_gather() {
    set +x
    echo "Running gpu-operator_gather ..."
    /usr/bin/gpu-operator_gather &> /dev/null

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
}

validate_gpu_operator_deployment() {
    trap collect_must_gather EXIT

    toolbox/gpu-operator/wait_deployment.sh
    toolbox/gpu-operator/run_gpu_burn.sh
}

test_master_branch() {
    prepare_cluster_for_gpu_operator
    toolbox/gpu-operator/deploy_from_operatorhub.sh --from-bundle=master

    validate_gpu_operator_deployment
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

    toolbox/gpu-operator/bundle_from_commit.sh "${gpu_operator_git_repo}" \
                                               "${gpu_operator_git_ref}" \
                                               "${GPU_OPERATOR_QUAY_BUNDLE_PUSH_SECRET}" \
                                               "${GPU_OPERATOR_QUAY_BUNDLE_IMAGE_NAME}" \
                                               "${CI_IMAGE_GPU_COMMIT_CI_IMAGE_UID}"

    toolbox/gpu-operator/deploy_from_operatorhub.sh "--from-bundle=${GPU_OPERATOR_QUAY_BUNDLE_IMAGE_NAME}:operator_bundle_gpu-operator-ci-image"

    validate_gpu_operator_deployment
}

test_operatorhub() {
    OPERATOR_VERSION="${1:-}"
    OPERATOR_CHANNEL="${2:-}"

    prepare_cluster_for_gpu_operator
    toolbox/gpu-operator/deploy_from_operatorhub.sh ${OPERATOR_VERSION} ${OPERATOR_CHANNEL}
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

undeploy_operatorhub() {
    toolbox/gpu-operator/undeploy_from_operatorhub.sh
}

if [ -z "${1:-}" ]; then
    echo "FATAL: $0 expects at least 1 argument ..."
    exit 1
fi

action="$1"
shift

set -x

case ${action} in
    "test_master_branch")
        test_master_branch "$@"
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
    "undeploy_operatorhub")
        undeploy_operatorhub "$@"
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
