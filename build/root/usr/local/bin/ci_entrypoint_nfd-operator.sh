#! /usr/bin/env bash

set -o pipefail
set -o errexit
set -o nounset

prepare_cluster_for_nfd() {
    if toolbox/nfd/has_nfd_labels.sh; then
        echo "FATAL: NFD labels found in the cluster"
        exit 1
    fi
    toolbox/cluster/capture_environment.sh
}

validate_nfd_deployment() {
    if ! toolbox/nfd/wait_nfd_labels.sh; then
        echo "FATAL: no NFD labels found."
        exit 1
    fi
}

test_master_branch() {
    CI_IMAGE_NFD_COMMIT_CI_REPO="${1:-https://github.com/openshift/cluster-nfd-operator.git}"
    CI_IMAGE_NFD_COMMIT_CI_REF="${2:-master}"

    echo "Using Git repository ${CI_IMAGE_NFD_COMMIT_CI_REPO} with ref ${CI_IMAGE_NFD_COMMIT_CI_REF}"

    CI_IMAGE_NFD_COMMIT_CI_IMAGE_TAG="ci-image"

    prepare_cluster_for_nfd
    toolbox/nfd-operator/deploy_from_commit.sh   "${CI_IMAGE_NFD_COMMIT_CI_REPO}" \
                                        "${CI_IMAGE_NFD_COMMIT_CI_REF}" \
                                        "${CI_IMAGE_NFD_COMMIT_CI_IMAGE_TAG}"
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
    -*)
        echo "FATAL: Unknown option: ${action}"
        exit 1
        ;;
    *)
        echo "FATAL: Unknown target \"${target}\""
        exit 1
        ;;
esac
