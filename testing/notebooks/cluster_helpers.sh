#! /bin/bash

cluster_helpers::get_compute_node_count() {
    local cluster_role=$1

    if [[ "$cluster_role" == "sutest" ]]; then

        if test_config clusters.sutest.compute.autoscaling.enabled; then
            echo 0
            return
        fi

        local NB_SIZE_CONFIG_KEY=rhods.notebooks.customize.notebook_size
        local notebook_cpu=$(get_config $NB_SIZE_CONFIG_KEY.cpu)
        local notebook_mem=$(get_config $NB_SIZE_CONFIG_KEY.mem_gi)

        NOTEBOOK_OAUTH_PROXY_CPU=0.1
        NOTEBOOK_OAUTH_PROXY_MEM=0.160 # mb # as shown in the node allocated resources. But 64Mb is what is in the spec ...

        local request_cpu=$(python3 -c "print(f'{$notebook_cpu + $NOTEBOOK_OAUTH_PROXY_CPU:.3f}')")
        local request_mem=$(python3 -c "print(f'{$notebook_mem + $NOTEBOOK_OAUTH_PROXY_MEM:.3f}')")
        local notebook_size="$request_cpu $request_mem"

        if test_config clusters.sutest.is_managed; then
            if test_config clusters.sutest.managed.is_ocm; then
                local instance_type="$(get_config clusters.create.ocm.compute.type)"
            else
                _error "Cannot get the instance type of ROSA clusters ..."
            fi
        else
            local instance_type="$(get_config clusters.create.ocp.compute.type)"
        fi

        local user_count=$(get_config tests.notebooks.users.count)

        if test_config tests.notebooks.ods_ci.only_create_notebooks; then
            user_count=1
        fi
    else
        if test_config clusters.driver.compute.autoscaling.enabled; then
            echo 0
            return
        fi

        local test_flavor=$(get_config tests.notebooks.test_flavor)
        if [[ "$test_flavor" == "locust" ]]; then
            local notebook_size="1 2" # 'cpu mem', must match roles/rhods_notebook_locust_scale_test/templates/locust_job.yaml
            local user_count=$(($(get_config tests.notebooks.locust.cpu_count) + 1))
        else
            local notebook_size="$(get_config tests.notebooks.test_pods.size.cpu) $(get_config tests.notebooks.test_pods.size.mem_gi)"
            local user_count=$(get_config tests.notebooks.users.count)

            local test_mode=$(get_config tests.notebooks.ods_ci.test_mode)
            if [[ "$test_mode" == burst || "$test_mode" == batch ]]; then
                user_count=$(get_config tests.notebooks.users.batch_size)
            fi
        fi

        local instance_type="$(get_config clusters.create.ocp.compute.type)"
    fi

    local size=$(bash -c "python3 $TESTING_NOTEBOOKS_DIR/sizing/sizing \
                   '$instance_type' \
                   '$user_count' \
                   $notebook_size \
                    >&2 \
                    > '${ARTIFACT_DIR:-/tmp}/${cluster_role}_sizing'; echo \$?")

    if [[ "$size" == 0 ]]; then
        _error "couldn't determine the number of nodes to request ..." >&2
    fi
    _info "Need $size $instance_type nodes for running $user_count users with cpu/mem=($notebook_size) ($cluster_role cluster)" > /dev/null # cannot print anything on stdout here
    echo "$size"
}

cluster_helpers::ocm_oc_login() {
    local managed_cluster_name=$(get_config clusters.sutest.managed.name)

    local api_url=$(ocm describe cluster "$managed_cluster_name" --json | jq -r .api.url)

    # do it in a subshell to avoid leaking the `KUBEADMIN_PASS` secret because of `set -x`
    bash -c '
    source "'$PSAP_ODS_SECRET_PATH'/create_osd_cluster.password"
    oc login "'$api_url'" \
             --username=kubeadmin \
             --password="$KUBEADMIN_PASS" \
             --insecure-skip-tls-verify
    '
}

cluster_helpers::connect_sutest_cluster() {
    touch "$KUBECONFIG_SUTEST"

    switch_sutest_cluster

    if ! test_config clusters.sutest.is_managed; then
        oc get clusterversion

        return
    fi

    local managed_cluster_name=$(get_config clusters.sutest.managed.name)
    if test_config clusters.sutest.managed.is_ocm; then

        cluster_helpers::ocm_login

        if [[ $((ocm describe cluster "$managed_cluster_name"  --json || true) | jq -r .state) != "ready" ]];
        then
            _error "OCM cluster '$managed_cluster_name' isn't ready ..."
        fi

        cluster_helpers::ocm_oc_login
    fi

    oc get clusterversion
}
