#! /bin/bash

driver_build_and_preload_image() {
    suffix=$1

    # this command may fail when the ImageStream operator isn't 100% ready
    process_ctrl::retry 5 30s \
                        ./run_toolbox.py from_config cluster build_push_image \
                        --suffix "$suffix"

    if test_config clusters.driver.compute.autoscaling.enabled; then
        return
    fi

    if ! test_config clusters.driver.compute.dedicated; then
        return
    fi

    ./run_toolbox.py from_config cluster preload_image \
                     --suffix "$suffix"
}

driver_build_and_preload_ods_ci_image() {
    driver_build_and_preload_image "ods-ci"
}

prepare_driver_cluster() {
    switch_cluster driver

    prepare_driver_scale_cluster

    local loadtest_namespace=$(get_config tests.notebooks.namespace)

    oc create namespace "$loadtest_namespace" -oyaml --dry-run=client | oc apply -f-

    set_dedicated_node_annotations() {
        # sets (or removes) the toleration/node-selector annotations on the $loadtest_namespace project

        local dedicated="{}" # set the toleration/node-selector annotations
        if ! test_config clusters.sutest.compute.dedicated; then
            dedicated="{value: ''}" # delete the toleration/node-selector annotations, if it exists
        fi

        ./run_toolbox.py from_config cluster set_project_annotation --prefix driver --suffix node_selector --extra "$dedicated"
        ./run_toolbox.py from_config cluster set_project_annotation --prefix driver --suffix toleration --extra "$dedicated"
    }

    # do not run this in background, we want to have the labels before running anything else
    set_dedicated_node_annotations

    process_ctrl::run_in_bg driver_build_and_preload_ods_ci_image
    process_ctrl::run_in_bg driver_build_and_preload_image "artifacts-exporter"

    process_ctrl::run_in_bg ./run_toolbox.py from_config cluster deploy_minio_s3_server
    process_ctrl::run_in_bg ./run_toolbox.py from_config cluster deploy_nginx_server

    process_ctrl::run_in_bg ./run_toolbox.py from_config cluster deploy_redis_server
}

prepare_driver_scale_cluster() {
    switch_driver_cluster

    if [[ "$(get_config clusters.create.type)" == "single" ]] && test_config clusters.sutest.is_metal; then
        _info "prepare_sutest_scale_cluster: bare-metal cluster, nothing to do."
        return
    fi

    local compute_nodes_count=$(get_config clusters.driver.compute.machineset.count)
    if [[ "$compute_nodes_count" == "null" ]]; then
        compute_nodes_count=$(cluster_helpers::get_compute_node_count driver)
    fi

    local driver_taint_key=$(get_config clusters.driver.compute.machineset.taint.key)
    local driver_taint_value=$(get_config clusters.driver.compute.machineset.taint.value)
    local driver_taint_effect=$(get_config clusters.driver.compute.machineset.taint.effect)
    local driver_taint="$driver_taint_key=$driver_taint_value:$driver_taint_effect"

    ./run_toolbox.py from_config cluster set_scale --prefix="driver" \
                     --extra "{scale: $compute_nodes_count}"


    if test_config clusters.driver.compute.autoscaling.enabled; then
        oc apply -f "$TESTING_NOTEBOOKS_DIR"/autoscaling/clusterautoscaler.yaml

        local machineset_name=$(get_config clusters.driver.compute.machineset.name)
        cat "$TESTING_NOTEBOOKS_DIR"/autoscaling/machineautoscaler.yaml \
            | sed "s/MACHINESET_NAME/$machineset_name/" \
            | oc apply -f-
    fi
}


driver_cleanup() {
    switch_driver_cluster

    local user_count=$(get_config tests.notebooks.users.count)

    skip_threshold=$(get_config tests.notebooks.cleanup.on_exit.skip_if_le_than_users)
    if [[ "$user_count" -le "$skip_threshold" ]]; then
        _info "Skip cluster cleanup (less that $skip_threshold users)"
        return
    fi

    if oc get cm/keep-cluster -n default 2>/dev/null; then
        _info "cm/keep-cluster found, not cleanup the cluster."
        return
    fi

    if ! test_config clusters.sutest.is_metal; then
       ./run_toolbox.py from_config cluster set_scale --prefix "driver" --suffix "cleanup" > /dev/null
    fi

    if test_config tests.notebooks.cleanup.on_exit.driver.delete_test_namespaces; then
        echo "Deleting the driver scale test namespaces"
        ods_ci_test_namespace=$(get_config tests.notebooks.namespace)
        statesignal_redis_namespace=$(get_command_arg namespace cluster deploy_redis_server)
        nginx_notebook_namespace=$(get_command_arg namespace cluster deploy_nginx_server)
        minio_namespace=$(get_command_arg namespace cluster deploy_minio_s3_server)

        oc delete namespace --ignore-not-found \
           "$ods_ci_test_namespace" \
           "$statesignal_redis_namespace" \
           "$nginx_notebook_namespace" \
           "$minio_namespace"
    fi
}
