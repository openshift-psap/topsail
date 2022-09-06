#! /bin/bash

set -o errexit
set -o pipefail
set -o nounset
set -o errtrace
set -x

THIS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
source "$THIS_DIR/process_ctrl.sh"
source "$THIS_DIR/common.sh"

if [[ -z "${KUBECONFIG_DRIVER:-}" ]]; then
    echo "ERROR: KUBECONFIG_DRIVER must be set"
    exit 1
fi

if [[ -z "${KUBECONFIG_SUTEST:-}" ]]; then
    echo "ERROR: KUBECONFIG_SUTEST must be set"
    exit 1
fi

prepare_driver_cluster() {
    cluster_role=driver

    export ARTIFACT_TOOLBOX_NAME_PREFIX="${cluster_role}_"
    export KUBECONFIG=$KUBECONFIG_DRIVER

    compute_nodes_type=$(get_compute_node_type "$cluster_role")
    compute_nodes_count=$(get_compute_node_count "$cluster_role" ocp "$compute_nodes_type")

    ./run_toolbox.py cluster set-scale "$compute_nodes_type" "$compute_nodes_count"
}

connect_sutest_cluster() {
    if [[ -z "${SUTEST_CLUSTER_NAME:-}" ]]; then
        echo "ERROR: SUTEST_CLUSTER_NAME must be set with the base name of the private cluster"
        exit 1
    fi

    if [[ -z "${SUTEST_CLUSTER_USER_NAME:-}" ]]; then
        echo "ERROR: SUTEST_CLUSTER_USER_NAME must be set with the username to use to log into the private cluster"
        exit 1
    fi

    rm -f "$KUBECONFIG_SUTEST"
    touch "$KUBECONFIG_SUTEST"

    export KUBECONFIG=$KUBECONFIG_SUTEST

    bash -ce '
      source "$PSAP_ODS_SECRET_PATH/get_cluster.password"
      oc login https://api.'$SUTEST_CLUSTER_NAME':6443 \
         --insecure-skip-tls-verify \
         --username='$SUTEST_CLUSTER_USER_NAME' \
         --password="$password"
     '
}

prepare_sutest_cluster() {
    cluster_role=sutest

    export ARTIFACT_TOOLBOX_NAME_PREFIX="${cluster_role}_"
    export KUBECONFIG=$KUBECONFIG_SUTEST

    compute_nodes_type=$(get_compute_node_type "$cluster_role")
    compute_nodes_count=$(get_compute_node_count "$cluster_role" ocp "$compute_nodes_type")
    ./run_toolbox.py cluster set-scale "$compute_nodes_type" "$compute_nodes_count"
}

unprepare_sutest_cluster() {
    cluster_role=sutest

    export ARTIFACT_TOOLBOX_NAME_PREFIX="${cluster_role}_"
    export KUBECONFIG=$KUBECONFIG_SUTEST

    compute_nodes_type=$(get_compute_node_type "$cluster_role")

    ./run_toolbox.py cluster set-scale "$compute_nodes_type" 0
}

unprepare_driver_cluster() {
    cluster_role=driver

    export ARTIFACT_TOOLBOX_NAME_PREFIX="${cluster_role}_"
    export KUBECONFIG=$KUBECONFIG_DRIVER

    compute_nodes_type=$(get_compute_node_type "$cluster_role")

    ./run_toolbox.py cluster set-scale "$compute_nodes_type" 0
}

action="${1:-}"
if [[ -z "${action}" ]]; then
    echo "FATAL: $0 expects 2 arguments: (create|destoy) CLUSTER_ROLE"
    exit 1
fi

shift

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
        echo "FATAL: Unknown action: ${action}" "$@"
        exit 1
        ;;
esac
