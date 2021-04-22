#! /usr/bin/env bash

set -o pipefail
set -o errexit
set -o nounset

prepare_cluster_for_sro() {
    source $ENTRY_LIB_DIR/entitle.sh 

    toolbox/cluster/capture_environment.sh

    entitle

    if ! toolbox/nfd/has_nfd_labels.sh; then
        toolbox/nfd/deploy_from_operatorhub.sh
    fi
}

validate_sro_deployment() {
    trap toolbox/special-resource-operator/capture_deployment_state.sh ERR

    toolbox/special-resource-operator/run_e2e_test.sh "${CI_IMAGE_SRO_COMMIT_CI_REPO}" "${CI_IMAGE_SRO_COMMIT_CI_REF}"

    trap - ERR
    toolbox/special-resource-operator/capture_deployment_state.sh
}

test_master_branch() {
    CI_IMAGE_SRO_COMMIT_CI_REPO="${1:-https://github.com/openshift-psap/special-resource-operator.git}"
    CI_IMAGE_SRO_COMMIT_CI_REF="${2:-master}"

    echo "Using Git repository ${CI_IMAGE_SRO_COMMIT_CI_REPO} with ref ${CI_IMAGE_SRO_COMMIT_CI_REF}"

    prepare_cluster_for_sro
    toolbox/special-resource-operator/deploy_from_commit.sh "${CI_IMAGE_SRO_COMMIT_CI_REPO}" \
                                               "${CI_IMAGE_SRO_COMMIT_CI_REF}"
    validate_sro_deployment
}

action="$1"
shift

set -x

case ${action:-} in
    "test_master_branch")
        test_master_branch "$@"
        exit 0
        ;;
    -*)
        echo "Unknown option: ${target:-}"
        exit 1
        ;;
    *)
        echo "Nothing to do ..."
        exit 1
        ;;
esac
