#! /usr/bin/env bash

set -o pipefail
set -o errexit
set -o nounset

prepare_cluster_for_sro() {
    ./run_toolbox.py cluster capture_environment
    entitle.sh

    if ! ./run_toolbox.py nfd has_labels; then
        ./run_toolbox.py nfd_operator deploy_from_operatorhub
    fi
}

validate_sro_deployment() {
    trap "./run_toolbox.py sro capture_deployment_state" EXIT

    ./run_toolbox.py sro run_e2e_test "${CI_IMAGE_SRO_COMMIT_CI_REPO}" "${CI_IMAGE_SRO_COMMIT_CI_REF}"
}

test_master_branch() {
    CI_IMAGE_SRO_COMMIT_CI_REPO="${1:-https://github.com/openshift-psap/special-resource-operator.git}"
    CI_IMAGE_SRO_COMMIT_CI_REF="${2:-master}"

    echo "Using Git repository ${CI_IMAGE_SRO_COMMIT_CI_REPO} with ref ${CI_IMAGE_SRO_COMMIT_CI_REF}"

    prepare_cluster_for_sro
    ./run_toolbox.py sro deploy_from_commit "${CI_IMAGE_SRO_COMMIT_CI_REPO}" \
                                    "${CI_IMAGE_SRO_COMMIT_CI_REF}"
    validate_sro_deployment
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
    *)
        echo "FATAL: Nothing to do ..."
        exit 1
        ;;
esac
