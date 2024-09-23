#! /bin/bash

DRIVER_CLUSTER=driver
SUTEST_CLUSTER=sutest

switch_sutest_cluster() {
    switch_cluster "$SUTEST_CLUSTER"
}

switch_driver_cluster() {
    switch_cluster "$DRIVER_CLUSTER"
}

switch_cluster() {
    local cluster_role="$1"
    echo "Switching to the '$cluster_role' cluster"
    if [[ "$cluster_role" == "$DRIVER_CLUSTER" ]]; then
        export KUBECONFIG=$KUBECONFIG_DRIVER
    elif [[ "$cluster_role" == "$SUTEST_CLUSTER" ]]; then
        export KUBECONFIG=$KUBECONFIG_SUTEST
    else
        echo "Requested to switch to an unknown cluster '$cluster_role', exiting."
        exit 1
    fi
    export ARTIFACT_TOOLBOX_NAME_PREFIX="${cluster_role}_"
}

generate_report_index() {
    python3 "$TESTING_UTILS_DIR/generate_plot_index.py" > "$ARTIFACT_DIR/reports_index.html" || true
}

capture_environment() {
    switch_sutest_cluster

    ./run_toolbox.py cluster capture_environment > /dev/null || true

    switch_driver_cluster
    ./run_toolbox.py cluster capture_environment > /dev/null || true
}

prepare_ci() {
    cluster_helpers::connect_sutest_cluster

    lab_ci_sutest_prepare

    trap "set +e; process_ctrl::kill_bg_processes; sutest_cleanup; driver_cleanup; exit 1" ERR
}

LAB_ENVIRONEMNT_PREPARE_SUTEST_FCT=lab_environment_prepare_sutest
LAB_ENVIRONEMNT_CLEANUP_SUTEST_FCT=lab_environment_cleanup_sutest

lab_ci_sutest_prepare() {
    lab_name=$(get_config clusters.sutest.lab.name)
    if [[ "$lab_name" == "null" ]]; then
        echo "No lab environment to prepare."
        return
    fi

    prepare_lab_file="$TESTING_NOTEBOOKS_DIR/prepare_lab_$lab_name.sh"
    if [[ ! -f "$prepare_lab_file" ]]; then
        _error "Lab '$lab_name' preparation file '$prepare_lab_file' does not exist :/"
    fi
    source "$prepare_lab_file"

    if [[ "$(type -t $LAB_ENVIRONEMNT_PREPARE_SUTEST_FCT)" != function \
              || "$(type -t $LAB_ENVIRONEMNT_CLEANUP_SUTEST_FCT)" != function ]];
    then
        _error "Lab '$lab_name' preparation file '$prepare_lab_environment' does not contain '$PREPARE_FCT' or '$LAB_ENVIRONEMNT_CLEANUP_SUTEST_FCT' functions :/"
    fi

    $LAB_ENVIRONEMNT_PREPARE_SUTEST_FCT # execute the function
}

lab_ci_sutest_cleanup() {
    lab_name=$(get_config clusters.sutest.lab.name)
    if [[ "$lab_name" == "null" ]]; then
        echo "No lab environment to cleanup."
        return
    fi

    prepare_lab_file="$TESTING_NOTEBOOKS_DIR/prepare_lab_$lab_name.sh"

    # all the import consistency verifications have been done in prepare_lab_ci

    source "$prepare_lab_file"

    $LAB_ENVIRONEMNT_CLEANUP_SUTEST_FCT # execute the function
}

prepare() {
    if [[ "${JOB_NAME_SAFE:-}" == "light" ||  "${JOB_NAME_SAFE:-}" == *"-light" ]]; then
        local user_count=$(get_config tests.notebooks.users.count)
        local light_test_user_count=$(get_config 'ci_presets.notebooks_light["tests.notebooks.users.count"]')
        if [[ "$user_count" -gt "$light_test_user_count" ]]; then
            _error "Job '$JOB_NAME_SAFE' shouldn't run with more than $light_test_user_count. Found $user_count."
            exit 1 # shouldn't be reached, but just to be 100% sure.
        fi
    fi

    process_ctrl::run_in_bg prepare_driver_cluster

    prepare_sutest_cluster
    sutest_wait_rhods_launch

    process_ctrl::wait_bg_processes
}
