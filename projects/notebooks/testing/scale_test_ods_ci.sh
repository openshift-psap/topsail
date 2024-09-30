#! /bin/bash

run_ods_ci_test() {
    switch_driver_cluster

    local test_mode=$(get_config tests.notebooks.ods_ci.test_mode)

    if ! test_config clusters.sutest.is_metal; then
        local nginx_namespace=$(get_command_arg namespace server deploy_nginx_server)
        local nginx_hostname=$(oc get route/nginx -n "$nginx_namespace" -ojsonpath={.spec.host})
        if [[ -z "$nginx_hostname" ]]; then
            _error "Could not get NGINX notebook server address ...."
        fi

        local notebook_name=$(get_config tests.notebooks.ipynb.notebook_filename)
        local notebook_url="http://$nginx_hostname/$notebook_name"

        local extra_notebook_url="notebook_url: '$notebook_url',"
    else
        local extra_notebook_url=""
    fi

    local failed=0

    if [[ "$test_mode" == null || "$test_mode" == simple ]]; then
        ./run_toolbox.py from_config notebooks ods_ci_scale_test \
                         --extra "{$extra_notebook_url sut_cluster_kubeconfig: '$KUBECONFIG_SUTEST'}" \
            || failed=1

        # quick access to these files
        local last_test_dir=$(printf "%s\n" "$ARTIFACT_DIR"/*__*/ | tail -1)
        cp "$last_test_dir/"{failed_tests,success_count} "$ARTIFACT_DIR" 2>/dev/null 2>/dev/null || true

        cp  "$CI_ARTIFACTS_FROM_CONFIG_FILE" "$last_test_dir/config.yaml" || true
        set_config matbench.test_directory "$last_test_dir"

    else
        _error "Unknown ODS-CI test mode: '$test_mode'"
    fi

    return $failed
}
