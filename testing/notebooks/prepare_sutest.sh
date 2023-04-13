#! /bin/bash

prepare_sutest_deploy_rhods() {
    switch_sutest_cluster

    if test_config clusters.sutest.is_managed; then
        prepare_managed_sutest_deploy_rhods
    else
        prepare_ocp_sutest_deploy_rhods
    fi
}

prepare_sutest_deploy_ldap() {
    switch_sutest_cluster

    process_ctrl::run_in_bg \
        ./run_toolbox.py from_config cluster deploy_ldap
}

prepare_sutest_scale_cluster() {
    local cluster_role=sutest

    if test_config clusters.sutest.is_metal; then
        _info "prepare_sutest_scale_cluster: bare-metal cluster, nothing to do."
        return
    fi

    switch_sutest_cluster

    local compute_nodes_count=$(get_config clusters.sutest.compute.machineset.count)
    if [[ "$compute_nodes_count" == "null" ]]; then
        compute_nodes_count=$(cluster_helpers::get_compute_node_count sutest)
    fi

    if test_config clusters.sutest.is_managed; then
        if test_config clusters.sutest.compute.autoscaling.enabled; then
            local specific_options=" \
                --enable-autoscaling \
                --min-replicas=2 \
                --max-replicas=20 \
                "
        else
            local specific_options=" \
                --replicas "$compute_nodes_count" \
                "
        fi

        if test_config clusters.sutest.managed.is_ocm; then
            local managed_cluster_name=$(get_config clusters.sutest.managed.name)
            local compute_nodes_type=$(get_config clusters.create.ocm.compute.type)
            local compute_nodes_machinepool_name=$(get_config clusters.sutest.compute.machineset.name)

            local sutest_taint_key=$(get_config clusters.sutest.compute.machineset.taint.key)
            local sutest_taint_value=$(get_config clusters.sutest.compute.machineset.taint.value)
            local sutest_taint_effect=$(get_config clusters.sutest.compute.machineset.taint.effect)
            local sutest_taint="$sutest_taint_key=$sutest_taint_value:$sutest_taint_effect"

            ocm create machinepool "$compute_nodes_machinepool_name" \
                --cluster "$managed_cluster_name" \
                --instance-type "$compute_nodes_type" \
                --taints "$sutest_taint" \
                --labels "$sutest_taint_key=$sutest_taint_value" \
                $specific_options
        elif test_config clusters.sutest.managed.is_rosa; then
            _error "prepare_sutest_scale_cluster not supported with rosa"
        fi
    else
        if test_config clusters.sutest.compute.autoscaling.enabled && test_config clusters.sutest.compute.machineset.spot; then
            touch "$ARTIFACT_DIR/spot_and_autoscaling"

            # create one auto-scaling machineset per (region)/zone of the base worker machinesets

            cluster_name=$(oc get machines -n openshift-machine-api -ojsonpath={.items[0].spec.providerSpec.value.tags[0].name} | cut -d/ -f3)
            worker_machinesets=$(oc get machinesets -n openshift-machine-api -oname | grep $cluster_name | cut -d/ -f2)

            oc apply -f "$TESTING_NOTEBOOKS_DIR"/autoscaling/clusterautoscaler.yaml
            for base_worker_machineset in $worker_machinesets; do
                region_zone=$(echo "$base_worker_machineset" | cut -d- -f6-)
                new_machineset_name="$(get_config clusters.sutest.compute.machineset.name)-$region_zone"

                ./run_toolbox.py from_config cluster set_scale --prefix="sutest" \
                                 --extra "{scale: 0, name: '$new_machineset_name', base_machineset: '$base_worker_machineset'}"

                tag_spot_machineset sutest "$new_machineset_name"

                cat "$TESTING_NOTEBOOKS_DIR"/autoscaling/machineautoscaler.yaml \
                    | sed "s/MACHINESET_NAME/$new_machineset_name/" \
                    | oc apply -f-
            done
        else
            if test_config clusters.sutest.compute.machineset.spot; then
                compute_nodes_count=$(python3 -c "print(round($compute_nodes_count * 1.1))")
                _info "SUTEST running with SPOT nodes, giving +10% of worker nodes --> $compute_nodes_count"
            fi
            ./run_toolbox.py from_config cluster set_scale --prefix="sutest" \
                             --extra "{scale: $compute_nodes_count}"

            if test_config clusters.sutest.compute.machineset.spot; then
                tag_spot_machineset sutest "$(get_config clusters.sutest.compute.machineset.name)"
            fi

            if test_config clusters.sutest.compute.autoscaling.enabled; then
                oc apply -f "$TESTING_NOTEBOOKS_DIR"/autoscaling/clusterautoscaler.yaml

                local machineset_name=$(get_config clusters.sutest.compute.machineset.name)
                cat "$TESTING_NOTEBOOKS_DIR"/autoscaling/machineautoscaler.yaml \
                    | sed "s/MACHINESET_NAME/$machineset_name/" \
                    | oc apply -f-
            fi
        fi
    fi
}

prepare_sutest_cluster() {
    switch_sutest_cluster
    prepare_sutest_deploy_rhods
    prepare_sutest_deploy_ldap
    prepare_sutest_scale_cluster
    prepare_rhods_admin_users
}

prepare_managed_sutest_deploy_rhods() {
    if test_config rhods.deploy_from_catalog; then
        process_ctrl::run_in_bg \
            ./run_toolbox.py from_config rhods deploy_ods
    else
        if test_config clusters.sutest.managed.is_rosa; then
            _error "prepare_managed_sutest_deploy_rhods not supported on ROSA when 'rhods.deploy_from_catalog' is set."
        fi
        local managed_cluster_name=$(get_config clusters.sutest.managed.name)
        local email="$(cat "$PSAP_ODS_SECRET_PATH/$(get_config secrets.addon_email_file)")"
        process_ctrl::run_in_bg \
            ./run_toolbox.py from_config rhods deploy_addon "$managed_cluster_name" "$email"
    fi
}

setup_brew_registry() {
    local token_file=$PSAP_ODS_SECRET_PATH/$(get_config secrets.brew_registry_redhat_io_token_file)

    "$TESTING_NOTEBOOKS_DIR"/brew.registry.redhat.io/setup.sh "$token_file"
}

prepare_ocp_sutest_deploy_rhods() {
    switch_sutest_cluster

    if oc get csv -n redhat-ods-operator -oname | grep rhods-operator --quiet; then
        _info "RHODS already installed, skipping."
        return
    fi

    setup_brew_registry

    process_ctrl::run_in_bg \
        process_ctrl::retry 5 3m \
            ./run_toolbox.py from_config rhods deploy_ods

    if ! oc get group/dedicated-admins >/dev/null 2>/dev/null; then
        echo "Create the dedicated-admins group"
        oc adm groups new dedicated-admins
        oc adm policy add-cluster-role-to-group cluster-admin dedicated-admins
    fi
}

sutest_customize_rhods_before_wait() {
    # nothing to do at the moment
    echo -n ""
}

sutest_customize_rhods_after_wait() {
    local sutest_taint_key=$(get_config clusters.sutest.compute.machineset.taint.key)
    oc patch odhdashboardconfig odh-dashboard-config --type=merge -p '{"spec":{"notebookController":{"notebookTolerationSettings": {"enabled": true, "key": "'$sutest_taint_key'"}}}}' -n redhat-ods-applications

    local pvc_size=$(get_config rhods.notebooks.customize.pvc_size)
    if [[ "$pvc_size" ]]; then
        oc patch odhdashboardconfig odh-dashboard-config --type=merge -p '{"spec":{"notebookController":{"pvcSize":"'$pvc_size'"}}}' -n redhat-ods-applications
    fi

    local NB_SIZE_CONFIG_KEY=rhods.notebooks.customize.notebook_size
    if test_config "$NB_SIZE_CONFIG_KEY.enabled"; then
        local name=$(get_config $NB_SIZE_CONFIG_KEY.name)
        local cpu=$(get_config $NB_SIZE_CONFIG_KEY.cpu)
        local mem=$(get_config $NB_SIZE_CONFIG_KEY.mem_gi)

        oc get odhdashboardconfig/odh-dashboard-config -n redhat-ods-applications -ojson \
            | jq '.spec.notebookSizes = [{"name": "'$name'", "resources": { "limits":{"cpu":"'$cpu'", "memory":"'$mem'Gi"}, "requests":{"cpu":"'$cpu'", "memory":"'$mem'Gi"}}}]' \
            | oc apply -f-
    fi

    # workaround for RHODS-7570: disable RHODS monitoring
    oc label namespace redhat-ods-monitoring openshift.io/cluster-monitoring-
    oc label namespace redhat-ods-monitoring openshift.io/user-monitoring=false --overwrite
}

prepare_rhods_admin_users() {
    local rhods_admin_roles=$(get_config rhods.admin.roles[])
    local rhods_admin_count=$(get_config rhods.admin.count)
    local user_prefix=$(get_config ldap.users.prefix)

    for i in $(seq 0 $((rhods_admin_count-1))); do
        user="$user_prefix$i"
        for role in $rhods_admin_roles; do
            echo "Giving the '$role' role to user '$user' ..."
            oc adm policy add-cluster-role-to-user "$role" "$user"
        done
    done
}

sutest_wait_rhods_launch() {
    switch_sutest_cluster

    local customize_key=rhods.notebooks.customize.enabled

    if test_config "$customize_key"; then
        sutest_customize_rhods_before_wait
    fi

    local dedicated="{}" # set the toleration/node-selector annotations
    if ! test_config clusters.sutest.compute.dedicated; then
        dedicated="{value: ''}" # delete the toleration/node-selector annotations, if it exists
    fi

    ./run_toolbox.py from_config cluster set_project_annotation --prefix sutest --suffix node_selector --extra "$dedicated"
    ./run_toolbox.py from_config cluster set_project_annotation --prefix sutest --suffix toleration --extra "$dedicated"

    ./run_toolbox.py rhods wait_ods

    if test_config rhods.operator.stop; then
        oc scale deploy/rhods-operator --replicas=0 -n redhat-ods-operator

        odh_nbc_image=$(get_config rhods.operator.odh_notebook_controller.image)
        if [[ "$odh_nbc_image" != null ]]; then
            oc set image deploy/odh-notebook-controller-manager "manager=$odh_nbc_image" -n redhat-ods-applications
            echo "$odh_nbc_image" > "$ARTIFACT_DIR/odh-notebook-controller-manager.image"
        fi

        odh_nbc_replicas=$(get_config rhods.operator.odh_notebook_controller.replicas)
        if [[ "$odh_nbc_replicas" != null ]]; then
            oc scale deploy/odh-notebook-controller-manager "--replicas=$odh_nbc_replicas" -n redhat-ods-applications
            echo "$odh_nbc_replicas" > "$ARTIFACT_DIR/odh-notebook-controller-manager.replicas"
        fi

        kf_nbc_image=$(get_config rhods.operator.images.notebook_controller_deployment)
        if [[ "$kf_nbc_image" != null ]]; then
            oc set image deploy/notebook-controller-deployment "manager=$kf_nbc_image" -n redhat-ods-applications
            echo "$kf_nbc_image" > "$ARTIFACT_DIR/notebook-controller-deployment.image"
        fi

        dashboard_image=$(get_config rhods.operator.dashboard.image)
        if [[ "$dashboard_image" != null ]]; then
            oc set image deploy/rhods-dashboard "rhods-dashboard=$dashboard_image" -n redhat-ods-applications
            echo "$dashboard_image" > "$ARTIFACT_DIR/dashboard.image"
        fi


        dashboard_replicas=$(get_config rhods.operator.dashboard.replicas)
        if [[ "$dashboard_replicas" != null ]]; then
            oc scale deploy/rhods-dashboard "--replicas=$dashboard_replicas" -n redhat-ods-applications
            echo "$dashboard_replicas" > "$ARTIFACT_DIR/dashboard.replicas"
        fi

        dashboard_resources_cpu=$(get_config rhods.operator.dashboard.resources_cpu)
        if [[ "$dashboard_resources_cpu" != null ]]; then
            oc set resources deploy/rhods-dashboard "--limits=cpu=$dashboard_resources_cpu" "--requests=cpu=$dashboard_resources_cpu" -n redhat-ods-applications
            echo "$dashboard_resources_cpu" > "$ARTIFACT_DIR/dashboard.resources_cpu"
        fi

        ./run_toolbox.py rhods wait_ods
    fi

    if test_config "$customize_key"; then
        sutest_customize_rhods_after_wait

        ./run_toolbox.py rhods wait_ods
    fi


    # preload the notebook image only if auto-scaling is disabled
    if ! test_config clusters.sutest.compute.autoscaling.enabled; then
        local rhods_notebook_image_name=$(get_config tests.notebooks.notebook.image_name)
        local rhods_notebook_image_tag=$(oc get istag -n redhat-ods-applications -oname \
                                             | cut -d/ -f2 \
                                             | grep "$rhods_notebook_image_name" \
                                             | cut -d: -f2 \
                                             | tail -1)

        notebook_image="image-registry.openshift-image-registry.svc:5000/redhat-ods-applications/$rhods_notebook_image_name:$rhods_notebook_image_tag"
        ./run_toolbox.py from_config cluster preload_image --suffix "notebook" \
                         --extra "{image:'$notebook_image',name:'$rhods_notebook_image_name'}"
    fi

    # for the rhods-notebooks project
    ./run_toolbox.py from_config cluster set_project_annotation --prefix sutest --suffix rhods_notebooks_node_selector --extra "$dedicated"
    ./run_toolbox.py from_config cluster set_project_annotation --prefix sutest --suffix rhods_notebooks_toleration --extra "$dedicated"
}


sutest_cleanup() {
    switch_sutest_cluster
    sutest_cleanup_ldap

    skip_threshold=$(get_config tests.notebooks.cleanup.skip_if_le_than_users)
    user_count=$(get_config tests.notebooks.users.count)
    if [[ "$user_count" -le "$skip_threshold" ]]; then
        _info "Skip cluster cleanup (less that $skip_threshold users)"
        return
    fi

    if ! ./run_toolbox.py from_config rhods cleanup_notebooks > /dev/null; then
        _warning "rhods notebook cleanup failed :("
    fi

    if test_config clusters.sutest.is_managed; then
        local managed_cluster_name=$(get_config clusters.sutest.managed.name)
        local sutest_machineset_name=$(get_config clusters.sutest.compute.machineset.name)

        if test_config clusters.sutest.managed.is_ocm; then
            ocm delete machinepool "$sutest_machineset_name" --cluster "$managed_cluster_name"
        elif test_config clusters.sutest.managed.is_rosa; then
            rosa delete machinepool "$sutest_machineset_name" --cluster "$managed_cluster_name"
        else
            _error "sutest_cleanup: managed cluster must be OCM or ROSA ..."
        fi
    elif test_config clusters.sutest.is_metal; then
         true # nothing to do
    else
        ./run_toolbox.py from_config cluster set_scale --prefix "sutest" --suffix "cleanup" > /dev/null
    fi
}

sutest_cleanup_ldap() {
    switch_sutest_cluster

    local test_flavor=$(get_config tests.notebooks.test_flavor)
    if [[ "$test_flavor" == "notebook-performance" ]]; then
        echo "Running the notebook-performance, nothing to cleanup"
        return
    fi

    if oc get cm/keep-cluster -n default 2>/dev/null; then
        _info "cm/keep-cluster found, not undeploying LDAP."
        return
    fi
    if test_config clusters.sutest.managed.is_ocm; then
        cluster_helpers::ocm_login
    fi
    ./run_toolbox.py from_config cluster undeploy_ldap  > /dev/null
}

sutest_cleanup_rhods() {
    local user_prefix=$(get_config ldap.users.prefix)

    switch_sutest_cluster

    oc delete namespaces -lopendatahub.io/dashboard=true >/dev/null
    # delete any leftover namespace (if the label ^^^ wasn't properly applied)
    oc get ns -oname | (grep "$user_prefix" || true) | xargs -r oc delete
    oc delete notebooks,pvc --all -n rhods-notebooks || true

    # restart all the RHODS pods, to cleanup their logs
    oc delete pods --all -n redhat-ods-applications

    ./run_toolbox.py rhods wait_ods
}
