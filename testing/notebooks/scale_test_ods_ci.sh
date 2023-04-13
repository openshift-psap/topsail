#! /bin/bash

run_ods_ci_scaleup_test() {
    local extra_notebook_url=$1
    local failed=0
    local scalup_users=$(get_config tests.notebooks.users.scaleups[])
    local BASE_ARTIFACT_DIR="$ARTIFACT_DIR"

    do_cleanup() {
        sutest_cleanup_rhods
    }

    do_cleanup

    local test_idx=0
    for user_count in $scalup_users; do
        echo "$(date) Launching $user_count users."
        set_config tests.notebooks.users.count "$user_count"
        set_config tests.notebooks.ods_ci.test_mode simple
        test_idx=$((test_idx + 1)) # start at 1, 0 is prepare_steps

        export ARTIFACT_DIR="$BASE_ARTIFACT_DIR/000__prepare_steps/$(printf "%03d" $test_idx)__prepare_scalup${test_idx}_${user_count}users"

        if ! prepare; then
            failed=1
            break
        fi

        export ARTIFACT_DIR="$BASE_ARTIFACT_DIR/$(printf "%03d" $test_idx)__scalup${test_idx}_${user_count}users"
        run_test || failed=1
        generate_plots || failed=1

        do_cleanup

        if [[ "$failed" == 1 ]]; then
            break
        fi

    done

    if ! test_config tests.notebooks.ods_ci.only_create_notebooks; then
        oc delete notebooks --all -A || true
    fi

    set_config matbench.test_directory "$BASE_ARTIFACT_DIR"
    export ARTIFACT_DIR="$BASE_ARTIFACT_DIR"

    return $failed
}

run_ods_ci_burst_test() {
    local extra_notebook_url=$1
    local failed=0

    # number of users to launch in one test
    local batch_size=$(get_config tests.notebooks.users.batch_size)
    # total number of users to launch
    local user_target_count=$(get_config tests.notebooks.users.count)
    local users_already_in=0

    while [[ $users_already_in -lt $user_target_count ]]; do

        # take care of the overflow
        if [[ $((users_already_in + batch_size)) -gt $user_target_count ]]; then
            batch_size=$((user_target_count - users_already_in)) # original value lost, but that's the last iteration
        fi

        echo "$(date) Launching $batch_size users. $users_already_in/$user_target_count already in the system."
        ./run_toolbox.py from_config rhods notebook_ods_ci_scale_test \
             --extra "{$extra_notebook_url
                       user_index_offset: $users_already_in,
                       user_count: '$batch_size',
                       sut_cluster_kubeconfig: '$KUBECONFIG_SUTEST'}" || failed=1


        local last_test_dir=$(printf "%s\n" "$ARTIFACT_DIR"/*__*/ | tail -1)

        cp  "$CI_ARTIFACTS_FROM_CONFIG_FILE" "$last_test_dir/config.yaml" || true
        cat > "$last_test_dir/settings.burst_test" <<EOF
test_mode=burst
user_target_count=$user_target_count
users_already_in=$users_already_in
batch_size=$(get_config tests.notebooks.users.batch_size)
EOF
        if [[ "$failed" == 1 ]]; then
            break
        fi
        users_already_in=$((users_already_in + batch_size))
    done

    if ! test_config tests.notebooks.ods_ci.only_create_notebooks; then
        oc delete notebooks --all -A || true
    fi

    set_config matbench.test_directory "$ARTIFACT_DIR"

    return $failed
}

run_ods_ci_test() {
    switch_driver_cluster

    local test_mode=$(get_config tests.notebooks.ods_ci.test_mode)

    if ! test_config clusters.sutest.is_metal; then
        local nginx_namespace=$(get_command_arg namespace cluster deploy_nginx_server)
        local nginx_hostname=$(oc get route/nginx -n "$nginx_namespace" -ojsonpath={.spec.host})

        local notebook_name=$(get_config tests.notebooks.ipynb.notebook_filename)
        local notebook_url="http://$nginx_hostname/$notebook_name"

        local extra_notebook_url="notebook_url: '$notebook_url',"
    else
        local extra_notebook_url=""
    fi

    local failed=0

    if [[ "$test_mode" == null || "$test_mode" == simple ]]; then
        ./run_toolbox.py from_config rhods notebook_ods_ci_scale_test \
                         --extra "{$extra_notebook_url sut_cluster_kubeconfig: '$KUBECONFIG_SUTEST'}" \
            || failed=1

        # quick access to these files
        local last_test_dir=$(printf "%s\n" "$ARTIFACT_DIR"/*__*/ | tail -1)
        cp "$last_test_dir/"{failed_tests,success_count} "$ARTIFACT_DIR" 2>/dev/null 2>/dev/null || true

        cp  "$CI_ARTIFACTS_FROM_CONFIG_FILE" "$last_test_dir/config.yaml" || true
        set_config matbench.test_directory "$last_test_dir"

    elif [[ "$test_mode" == burst ]]; then
        run_ods_ci_burst_test "$extra_notebook_url" || failed=1
    elif [[ "$test_mode" == scaleup ]]; then
        run_ods_ci_scaleup_test "$extra_notebook_url" || failed=1
    else
        _error "Unknown ODS-CI test mode: '$test_mode'"
    fi

    return $failed
}
