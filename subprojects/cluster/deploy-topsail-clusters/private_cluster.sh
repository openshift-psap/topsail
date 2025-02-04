#! /bin/bash

set -o errexit
set -o pipefail
set -o nounset
set -o errtrace
set -x

TESTING_UTILS_OCP_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
TESTING_UTILS_DIR="${TESTING_UTILS_OCP_DIR}/.."

source "$TESTING_UTILS_DIR/logging.sh"
source "$TESTING_UTILS_DIR/process_ctrl.sh"
source "$TESTING_UTILS_DIR/configure.sh"

HOSTNAME_KEY=clusters.create.sutest.already_exists.hostname
USERNAME_KEY=clusters.create.sutest_already_exists.username

prepare_driver_cluster() {
    local cluster_role=driver

    export ARTIFACT_TOOLBOX_NAME_PREFIX="${cluster_role}_"
    export KUBECONFIG=$KUBECONFIG_DRIVER

    # nothing to do at the moment
}

connect_sutest_cluster() {
    local cluster_hostname=$(get_config "$HOSTNAME_KEY")
    if [[ "$cluster_hostname" == null ]]; then
        _error "$HOSTNAME_KEY must be set with the hostname of the private cluster, or with the PR argument 1."
    fi

    local cluster_username=$(get_config "$USERNAME_KEY")
    if [[ "$cluster_username" == null ]]; then
        _error "$USERNAME_KEY must be set with the username to use to log into the private cluster, or with the PR argument 2."
    fi

    rm -f "$KUBECONFIG_SUTEST"
    touch "$KUBECONFIG_SUTEST"

    export KUBECONFIG=$KUBECONFIG_SUTEST

    bash -ce '
      source "$PSAP_ODS_SECRET_PATH/get_cluster.password"
      oc login https://api.'$cluster_hostname':6443 \
         --insecure-skip-tls-verify \
         --username='$cluster_username' \
         --password="$password"
     '
}

prepare_sutest_cluster() {
    local cluster_role=sutest

    export ARTIFACT_TOOLBOX_NAME_PREFIX="${cluster_role}_"
    export KUBECONFIG=$KUBECONFIG_SUTEST

    # nothing to do at the moment
}

unprepare_sutest_cluster() {
    local cluster_role=sutest

    export ARTIFACT_TOOLBOX_NAME_PREFIX="${cluster_role}_"
    export KUBECONFIG=$KUBECONFIG_SUTEST

    # nothing to do at the moment
}

unprepare_driver_cluster() {
    local cluster_role=driver

    export ARTIFACT_TOOLBOX_NAME_PREFIX="${cluster_role}_"
    export KUBECONFIG=$KUBECONFIG_DRIVER

    # nothing to do at the moment
}

main() {
    if [[ -z "${KUBECONFIG_DRIVER:-}" ]]; then
        _error "KUBECONFIG_DRIVER must be set"
    fi

    if [[ -z "${KUBECONFIG_SUTEST:-}" ]]; then
        _error "KUBECONFIG_SUTEST must be set"
    fi

    if [[ -z "${ARTIFACT_DIR:-}" ]]; then
        _error "artifacts storage directory ARTIFACT_DIR not set ..."
        exit 1
    fi

    local action="${1:-}"

    set -x

    case ${action} in
        "connect_sutest_cluster")
            connect_sutest_cluster
            exit 0
            ;;
        "prepare_sutest_cluster")
            prepare_sutest_cluster
            exit 0
            ;;
        "prepare_driver_cluster")
            prepare_driver_cluster
            exit 0
            ;;
        "unprepare_sutest_cluster")
            unprepare_sutest_cluster
            exit 0
            ;;
        "unprepare_driver_cluster")
            unprepare_driver_cluster
            exit 0
            ;;
        *)
            echo "FATAL: Unknown action: ${action}"
            exit 1
            ;;
    esac
}

main "$@"
