#! /bin/bash

set -o errexit
set -o pipefail
set -o nounset
set -o errtrace
set -x

THIS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
source "$THIS_DIR/common.sh"
source "$THIS_DIR/process_ctrl.sh"
source "$THIS_DIR/../prow/_logging.sh"

export KUBECONFIG_DRIVER=$KUBECONFIG
export KUBECONFIG_SUTEST=/tmp/sutest_kubeconfig

if [[ -z "${SUTEST_CLUSTER_NAME:-}" ]]; then
    echo "ERROR: SUTEST_CLUSTER_NAME must be set with the base name of the private cluster"
    exit 1
fi

if [[ -z "${SUTEST_CLUSTER_USER_NAME:-}" ]]; then
    echo "ERROR: SUTEST_CLUSTER_USER_NAME must be set with the username to use to log into the private cluster"
    exit 1
fi

prepare_driver_cluster() {
    process_ctrl::run_in_bg "$THIS_DIR/private_cluster.sh" prepare_driver_cluster
    "$THIS_DIR/notebook_ux_e2e_scale_test.sh" prepare_driver_cluster
}

action=${1:-}

"$THIS_DIR/private_cluster.sh" connect_sutest_cluster

if [[ "$action" != "run" ]]; then
    process_ctrl::run_in_bg "$THIS_DIR/private_cluster.sh" prepare_sutest_cluster
    process_ctrl::run_in_bg prepare_driver_cluster

    process_ctrl::wait_bg_processes

fi

"$THIS_DIR/notebook_ux_e2e_scale_test.sh" run_test_and_plot

if [[ "$action" != "run" ]]; then
    process_ctrl::run_in_bg "$THIS_DIR/private_cluster.sh" unprepare_sutest_cluster
    process_ctrl::run_in_bg "$THIS_DIR/private_cluster.sh" unprepare_driver_cluster
fi
