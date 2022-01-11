#! /usr/bin/env bash

set -o pipefail
set -o errexit
set -o nounset

THIS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd ${THIS_DIR}/../..

nfd_git_repo=https://github.com/openshift/cluster-nfd-operator.git

_expected_fail() {
    # mark the last toolbox step as an expected fail (for clearer
    # parsing/display in ci-dashboard)
    # eg: if cluster doesn't have NFD labels (expected fail), deploy NFD
    # eg: if cluster doesn't have GPU nodes (expected fail), scale up with GPU nodes

    last_toolbox_dir=$(ls ${ARTIFACT_DIR}/*__* -d | tail -1)
    echo "$1" > ${last_toolbox_dir}/EXPECTED_FAIL
}

prepare_cluster_for_nfd() {
    if ./run_toolbox.py nfd has_labels; then
        echo "FATAL: NFD labels found in the cluster"
        exit 1
    fi

    # mark the failure of "nfd has_labels" ^^^ as expected
    _expected_fail "Checking if the cluster had NFD labels"

    ./run_toolbox.py cluster capture_environment
}

validate_nfd_deployment() {
    if ! ./run_toolbox.py nfd wait_labels; then
        echo "FATAL: no NFD labels found."
        exit 1
    fi
}

test_master_branch() {
    CI_IMAGE_NFD_COMMIT_CI_REPO="${1:-$nfd_git_repo}"
    CI_IMAGE_NFD_COMMIT_CI_REF="${2:-master}"

    echo "Using Git repository ${CI_IMAGE_NFD_COMMIT_CI_REPO} with ref ${CI_IMAGE_NFD_COMMIT_CI_REF}"

    CI_IMAGE_NFD_COMMIT_CI_IMAGE_TAG="ci-image"

    prepare_cluster_for_nfd
    ./run_toolbox.py nfd_operator deploy_from_commit "${CI_IMAGE_NFD_COMMIT_CI_REPO}" \
                                             "${CI_IMAGE_NFD_COMMIT_CI_REF}"  \
                                             --image-tag="${CI_IMAGE_NFD_COMMIT_CI_IMAGE_TAG}"
    validate_nfd_deployment
}

test_branch() {
    CI_IMAGE_NFD_COMMIT_CI_REPO="${1:-$nfd_git_repo}"
    CI_IMAGE_NFD_COMMIT_CI_REF="${2:-}"

    test "$CI_IMAGE_NFD_COMMIT_CI_REF" || {
    CI_IMAGE_NFD_COMMIT_CI_REF=release-$(oc get clusterversion -o jsonpath='{.items[].status.desired.version}' | grep -Po '^\d+\.\d+')
    }

    echo "Using Git repository ${CI_IMAGE_NFD_COMMIT_CI_REPO} with ref ${CI_IMAGE_NFD_COMMIT_CI_REF}"

    CI_IMAGE_NFD_COMMIT_CI_IMAGE_TAG="ci-image"

    prepare_cluster_for_nfd
    ./run_toolbox.py nfd_operator deploy_from_commit "${CI_IMAGE_NFD_COMMIT_CI_REPO}" \
                                             "${CI_IMAGE_NFD_COMMIT_CI_REF}"  \
                                             --image-tag="${CI_IMAGE_NFD_COMMIT_CI_IMAGE_TAG}"
    validate_nfd_deployment
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
    "test_branch")
        test_branch "$@"
        exit 0
        ;;
    *)
        echo "FATAL: Unknown target \"${target}\""
        exit 1
        ;;
esac
