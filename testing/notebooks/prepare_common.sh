#! /bin/bash

tag_spot_machineset() {
    local cluster_role="$1"
    local name="$2"

    local spot_tags=$(get_config clusters.create.ocp.spot.tags)
    local cluster_tags=$(get_config clusters.create.ocp.tags)
    local tags=$((echo -e "$spot_tags\n$cluster_tags") | jq -s '.[0] * .[1]' |  jq '. | to_entries | .[]' --compact-output)
    while read tag; do
        local tag_key=$(echo "$tag" | jq .key -r)
        local tag_value=$(echo "$tag" | jq .value -r)

        oc get machineset "$name" -ojson -n openshift-machine-api \
            | jq \
                  --arg name "$tag_key" \
                  --arg value "$tag_value" \
                  '.spec.template.spec.providerSpec.value.tags += [{"name": $name, "value": $value}]' \
            | oc apply -f-
    done <<< "$tags"

    oc get machineset "$name" -oyaml -n openshift-machine-api > "$ARTIFACT_DIR/${cluster_role}_machineset_spot_tagged.yaml"
}

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

prepare_notebook_performance_without_rhods() {
    local namespace=$(get_command_arg namespace rhods benchmark_notebook_performance)
    oc create namespace "$namespace" -oyaml --dry-run=client | oc apply -f-

    local dedicated="{}" # set the toleration/node-selector annotations
    if ! test_config clusters.sutest.compute.dedicated; then
        dedicated="{value: ''}" # delete the toleration/node-selector annotations, if it exists
    fi

    ./run_toolbox.py from_config cluster set_project_annotation --prefix sutest --suffix single_notebook_node_selector --extra "$dedicated"
    ./run_toolbox.py from_config cluster set_project_annotation --prefix sutest --suffix single_notebook_toleration --extra "$dedicated"
}

prepare() {
    prepare_notebook_performance_without_rhods

    local test_flavor=$(get_config tests.notebooks.test_flavor)
    if [[ "$test_flavor" == "notebook-performance" ]]; then

        if ! test_config tests.notebooks.notebook_performance.use_rhods; then
            _info "Skip cluster preparation (running the notebook-performance test without using RHODS)"

            return
        fi
    fi

    if [[ "${JOB_NAME_SAFE:-}" == "light" ||  "${JOB_NAME_SAFE:-}" == *"-light" ]]; then
        local user_count=$(get_config tests.notebooks.users.count)
        local light_test_user_count=$(get_config 'ci_presets.notebooks_light["tests.notebooks.users.count"]')
        if [[ "$user_count" -gt "$light_test_user_count" ]]; then
            _error "Job '$JOB_NAME_SAFE' shouldn't run with more than $light_test_user_count. Found $user_count."
            exit 1 # shouldn't be reached, but just to be 100% sure.
        fi
    fi

    process_ctrl::run_in_bg prepare_sutest_cluster
    process_ctrl::run_in_bg prepare_driver_cluster

    process_ctrl::wait_bg_processes

    sutest_wait_rhods_launch
}
