#! /usr/bin/env bash

set -o pipefail
set -o errexit
set -o nounset

THIS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd ${THIS_DIR}/../..

prepare_cluster_for_sro() {
    ./run_toolbox.py cluster capture_environment

    finalizers+=("./run_toolbox.py entitlement undeploy")

    ${THIS_DIR}/entitle.sh

    if ! ./run_toolbox.py nfd has_labels; then
        if oc get packagemanifests/nfd -n openshift-marketplace > /dev/null; then
            ./run_toolbox.py nfd_operator deploy_from_operatorhub
        else
            # in 4.9, NFD is currently not available from its default location,
            touch "${ARTIFACT_DIR}/NFD_DEPLOYED_FROM_MASTER"
            # install the NFD Operator from sources
            CI_IMAGE_NFD_COMMIT_CI_REPO="${1:-https://github.com/openshift/cluster-nfd-operator.git}"
            CI_IMAGE_NFD_COMMIT_CI_REF="${2:-master}"
            CI_IMAGE_NFD_COMMIT_CI_IMAGE_TAG="ci-image"
            ./run_toolbox.py nfd_operator deploy_from_commit "${CI_IMAGE_NFD_COMMIT_CI_REPO}" \
                             "${CI_IMAGE_NFD_COMMIT_CI_REF}"  \
                             --image-tag="${CI_IMAGE_NFD_COMMIT_CI_IMAGE_TAG}"
        fi
    fi
}

validate_sro_deployment() {
    finalizers+=("./run_toolbox.py sro capture_deployment_state")

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

finalizers=()
run_finalizers() {
    [ ${#finalizers[@]} -eq 0 ] && return

    echo "Running exit finalizers ..."
    for finalizer in "${finalizers[@]}"
    do
        echo "$finalizer"
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
