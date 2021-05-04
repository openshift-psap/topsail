#! /usr/bin/env bash

set -o pipefail
set -o errexit
set -o nounset

prepare_cluster_for_gpu_operator() {
    trap collect_must_gather ERR

    toolbox/cluster/capture_environment.sh
    entitle.sh

    if ! toolbox/nfd/has_nfd_labels.sh; then
        toolbox/nfd/deploy_from_operatorhub.sh
    fi

    if ! toolbox/nfd/has_gpu_nodes.sh; then
        toolbox/cluster/set_scale.sh g4dn.xlarge 1
        toolbox/nfd/wait_gpu_nodes.sh
    fi
}

collect_must_gather() {
    /usr/bin/gpu-operator_gather
    DEST="${ARTIFACT_DIR}/$(date +%H%M%S)__gpu-operator__must-gather"
    mkdir -p "$DEST"
    cp -r /must-gather/* "$DEST"
}

validate_gpu_operator_deployment() {
    trap collect_must_gather ERR EXIT

    toolbox/gpu-operator/wait_deployment.sh
    toolbox/gpu-operator/run_gpu_burn.sh
}

test_master_branch() {
    prepare_cluster_for_gpu_operator
    toolbox/gpu-operator/deploy_from_operatorhub.sh --from-bundle=master

    validate_gpu_operator_deployment
}

test_commit() {
    CI_IMAGE_GPU_COMMIT_CI_REPO="${1:-https://github.com/NVIDIA/gpu-operator.git}"
    CI_IMAGE_GPU_COMMIT_CI_REF="${2:-master}"

    CI_IMAGE_GPU_COMMIT_CI_IMAGE_UID="ci-image"

    echo "Using Git repository ${CI_IMAGE_GPU_COMMIT_CI_REPO} with ref ${CI_IMAGE_GPU_COMMIT_CI_REF}"

    prepare_cluster_for_gpu_operator
    toolbox/gpu-operator/deploy_from_commit.sh "${CI_IMAGE_GPU_COMMIT_CI_REPO}" \
                                               "${CI_IMAGE_GPU_COMMIT_CI_REF}" \
                                               "${CI_IMAGE_GPU_COMMIT_CI_IMAGE_UID}"
    validate_gpu_operator_deployment
}

test_operatorhub() {
    OPERATOR_VERSION="${1:-}"
    prepare_cluster_for_gpu_operator
    toolbox/gpu-operator/deploy_from_operatorhub.sh ${OPERATOR_VERSION}
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

case ${action:-} in
    "test_master_branch")
        test_master_branch "$@"
        exit 0
        ;;
    "test_commit")
        test_commit "$@"
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
