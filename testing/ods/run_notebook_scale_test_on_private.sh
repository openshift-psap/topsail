#! /bin/bash

set -o errexit
set -o pipefail
set -o nounset
set -o errtrace
set -x

TESTING_ODS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

source "$TESTING_ODS_DIR/process_ctrl.sh"
source "$TESTING_ODS_DIR/../_logging.sh"
source "$TESTING_ODS_DIR/config_common.sh"
source "$TESTING_ODS_DIR/config_clusters.sh"
source "$TESTING_ODS_DIR/config_load_overrides.sh"

source "$TESTING_ODS_DIR/cluster_helpers.sh"

export KUBECONFIG_DRIVER=$KUBECONFIG
export KUBECONFIG_SUTEST=/tmp/sutest_kubeconfig

HOSTNAME_KEY=clusters.create.sutest.already_exists.hostname
USERNAME_KEY=clusters.create.sutest_already_exists.username

set_config_from_pr_arg 0 "$HOSTNAME_KEY"
set_config_from_pr_arg 1 "$USERNAME_KEY"

cluster_hostname=$(get_config "$HOSTNAME_KEY")
if [[ -z "$cluster_hostname" ]]; then
    _error "$HOSTNAME_KEY must be set with the hostname of the private cluster, or with the PR argument 0"
fi

cluster_username=$(get_config "$USERNAME_KEY")
if [[ -z "$cluster_username" ]]; then
    _error "$USERNAME_KEY must be set with the username to use to log into the private cluster, or with the PR argument 1"
fi

prepare_driver_cluster() {
    process_ctrl::run_in_bg "$TESTING_ODS_DIR/private_cluster.sh" prepare_driver_cluster
    "$TESTING_ODS_DIR/notebook_scale_test.sh" prepare_driver_cluster
}

action=${1:-}

"$TESTING_ODS_DIR/private_cluster.sh" connect_sutest_cluster

if [[ "$action" == "prepare" ]]; then
    process_ctrl::run_in_bg "$TESTING_ODS_DIR/private_cluster.sh" prepare_sutest_cluster
    process_ctrl::run_in_bg prepare_driver_cluster

    process_ctrl::wait_bg_processes
else
    "$TESTING_ODS_DIR/notebook_scale_test.sh" run_test_and_plot

    if [[ "$action" != "run" ]]; then
        process_ctrl::run_in_bg "$TESTING_ODS_DIR/private_cluster.sh" unprepare_sutest_cluster
        process_ctrl::run_in_bg "$TESTING_ODS_DIR/private_cluster.sh" unprepare_driver_cluster
    fi
fi
