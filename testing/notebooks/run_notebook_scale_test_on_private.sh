#! /bin/bash

set -o errexit
set -o pipefail
set -o nounset
set -o errtrace
set -x

TESTING_NOTEBOOKS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
TESTING_UTILS_DIR="$TESTING_NOTEBOOKS_DIR/../utils"

source "$TESTING_UTILS_DIR/process_ctrl.sh"
source "$TESTING_UTILS_DIR/logging.sh"
source "$TESTING_NOTEBOOKS_DIR/configure.sh"
source "$TESTING_NOTEBOOKS_DIR/cluster_helpers.sh"

export KUBECONFIG_DRIVER=$KUBECONFIG
export KUBECONFIG_SUTEST=/tmp/sutest_kubeconfig

HOSTNAME_KEY=clusters.create.sutest.already_exists.hostname
USERNAME_KEY=clusters.create.sutest_already_exists.username


main() {
    "$TESTING_UTILS_DIR/ci_init_configure.sh"

    set_config_from_pr_arg 1 "$HOSTNAME_KEY"
    set_config_from_pr_arg 2 "$USERNAME_KEY"

    cluster_hostname=$(get_config "$HOSTNAME_KEY")
    if [[ "$cluster_hostname" == null ]]; then
        _error "$HOSTNAME_KEY must be set with the hostname of the private cluster, or with the PR argument 0"
    fi

    cluster_username=$(get_config "$USERNAME_KEY")
    if [[ "$cluster_username" == null ]]; then
        local pr_author=$(echo "$JOB_SPEC" | jq -r .refs.pulls[0].author)
        set_config "$USERNAME_KEY" "$pr_author"
    fi

    prepare_driver_cluster() {
        process_ctrl::run_in_bg "$TESTING_UTILS_DIR/openshift_clusters/private_cluster.sh" prepare_driver_cluster
        "$TESTING_NOTEBOOKS_DIR/scale_test.sh" prepare_driver_cluster
    }

    action=${1:-}

    "$TESTING_UTILS_DIR/openshift_clusters/private_cluster.sh" connect_sutest_cluster

    if [[ "$action" == "prepare" ]]; then
        process_ctrl::run_in_bg "$TESTING_UTILS_DIR/openshift_clusters/private_cluster.sh" prepare_sutest_cluster
        process_ctrl::run_in_bg prepare_driver_cluster

        process_ctrl::wait_bg_processes
    else
        "$TESTING_NOTEBOOKS_DIR/
scale_test.sh" run_test_and_plot

        if [[ "$action" != "run" ]]; then
            process_ctrl::run_in_bg "$TESTING_UTILS_DIR/openshift_clusters/private_cluster.sh" unprepare_sutest_cluster
            process_ctrl::run_in_bg "$TESTING_UTILS_DIR/openshift_clusters/private_cluster.sh" unprepare_driver_cluster
        fi
    fi
}

main "$@"
