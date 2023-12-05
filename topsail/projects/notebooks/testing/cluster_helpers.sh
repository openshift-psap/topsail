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

        local instance_type="$(get_config clusters.create.ocp.compute.type)"

        local user_count=$(get_config tests.notebooks.users.count)

        if test_config tests.notebooks.ods_ci.only_create_notebooks; then
            user_count=1
        fi
    else
        if test_config clusters.driver.compute.autoscaling.enabled; then
            echo 0
            return
        fi

        local notebook_size="$(get_config tests.notebooks.test_pods.size.cpu) $(get_config tests.notebooks.test_pods.size.mem_gi)"
        local user_count=$(get_config tests.notebooks.users.count)

        local instance_type="$(get_config clusters.create.ocp.compute.type)"
    fi

    local size=$(bash -c "python3 $TESTING_UTILS_DIR/sizing/sizing \
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

cluster_helpers::connect_sutest_cluster() {
    touch "$KUBECONFIG_SUTEST"

    switch_sutest_cluster

    oc get clusterversion
}
