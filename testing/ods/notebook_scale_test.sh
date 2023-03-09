#! /bin/bash

set -o errexit
set -o pipefail
set -o nounset
set -o errtrace
set -x

TESTING_ODS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

if [ -z "${ARTIFACT_DIR:-}" ]; then
    if [[ "${INSIDE_CI_IMAGE:-}" == "y" ]]; then
        echo "ARTIFACT_DIR not set, cannot proceed without inside the image."
        false
    fi

    export ARTIFACT_DIR="${CI_ARTIFACT_BASE_DIR:-/tmp}/ci-artifacts_$(date +%Y%m%d)"
    mkdir -p "$ARTIFACT_DIR"

    echo "Using ARTIFACT_DIR=$ARTIFACT_DIR as default artifacts directory."
else
    echo "Using ARTIFACT_DIR=$ARTIFACT_DIR."
fi

source "$TESTING_ODS_DIR/../_logging.sh"
source "$TESTING_ODS_DIR/../process_ctrl.sh"
source "$TESTING_ODS_DIR/configure.sh"
source "$TESTING_ODS_DIR/cluster_helpers.sh"

KUBECONFIG_DRIVER="${KUBECONFIG_DRIVER:-${KUBECONFIG:-}}" # cluster driving the test
KUBECONFIG_SUTEST="${KUBECONFIG_SUTEST:-${KUBECONFIG:-}}" # system under test


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

# ---

build_and_preload_image() {
    suffix=$1

    process_ctrl::retry 5 30s \
                        ./run_toolbox.py from_config utils build_push_image \
                        --suffix "$suffix"
    ./run_toolbox.py from_config cluster preload_image \
                     --suffix "$suffix"
}

build_and_preload_ods_ci_image() {
    build_and_preload_image "ods-ci"
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

    process_ctrl::run_in_bg build_and_preload_ods_ci_image
    process_ctrl::run_in_bg build_and_preload_image "locust"
    process_ctrl::run_in_bg build_and_preload_image "artifacts-exporter"

    process_ctrl::run_in_bg ./run_toolbox.py from_config cluster deploy_minio_s3_server
    process_ctrl::run_in_bg ./run_toolbox.py from_config cluster deploy_nginx_server

    process_ctrl::run_in_bg ./run_toolbox.py from_config cluster deploy_redis_server
}

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
        if test_config clusters.sutest.compute.autoscaling.enable; then
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
        ./run_toolbox.py from_config cluster set_scale --prefix="sutest" \
                         --extra "{scale: $compute_nodes_count}"

        if test_config clusters.sutest.compute.autoscaling.enabled; then
            oc apply -f testing/ods/autoscaling/clusterautoscaler.yaml

            local machineset_name=$(get_config clusters.sutest.compute.machineset.name)
            cat testing/ods/autoscaling/machineautoscaler.yaml \
                | sed "s/MACHINESET_NAME/$machineset_name/" \
                | oc apply -f-
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

    "$TESTING_ODS_DIR"/brew.registry.redhat.io/setup.sh "$token_file"
}

prepare_ocp_sutest_deploy_rhods() {
    switch_sutest_cluster

    if oc get csv -n redhat-ods-operator -oname | grep rhods-operator --quiet; then
        _info "RHODS already installed, skipping."
        return
    fi

    setup_brew_registry

    # https://issues.redhat.com/browse/RHODS-5203
    oc create namespace "anonymous" -oyaml --dry-run=client | oc apply -f-

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
    if test_config rhods.notebooks.customize.remove_gpu_images; then
        # Fill the imagestreams with dummy (ubi) images
        for image in minimal-gpu nvidia-cuda-11.4.2 pytorch tensorflow; do
            oc tag registry.access.redhat.com/ubi8/ubi "$image:ubi" -n redhat-ods-applications
        done
        # Delete the RHODS builds
        oc delete builds --all  -n redhat-ods-applications
    fi
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

        if test_config rhods.operator.remove_oauth_resources; then
            oc get deploy rhods-dashboard -ojson | jq 'del(.spec.template.spec.containers[1].resources)' -n redhat-ods-applications | oc apply -f-
            echo "removed" > "$ARTIFACT_DIR/dashboard.oauth.resources"
        fi
    fi

    local dedicated="{}" # set the toleration/node-selector annotations
    if ! test_config clusters.sutest.compute.dedicated; then
        dedicated="{value: ''}" # delete the toleration/node-selector annotations, if it exists
    fi

    ./run_toolbox.py from_config cluster set_project_annotation --prefix sutest --suffix node_selector --extra "$dedicated"
    ./run_toolbox.py from_config cluster set_project_annotation --prefix sutest --suffix toleration --extra "$dedicated"

    ./run_toolbox.py rhods wait_ods

    if test_config "$customize_key"; then
        sutest_customize_rhods_after_wait

        ./run_toolbox.py rhods wait_ods
    fi


    if ! test_config clusters.sutest.compute.autoscaling.enable; then
        local rhods_notebook_image_name=$(get_config tests.notebooks.notebook.image_name)
        local rhods_notebook_image_tag=$(oc get istag -n redhat-ods-applications -oname \
                                       | cut -d/ -f2 | grep "$rhods_notebook_image_name" | cut -d: -f2)

        # preload the image only if auto-scaling is disabled
        notebook_image="image-registry.openshift-image-registry.svc:5000/redhat-ods-applications/$rhods_notebook_image_name:$rhods_notebook_image_tag"
        ./run_toolbox.py from_config cluster preload_image --suffix "notebook" \
                         --extra "{image:'$notebook_image',name:'$rhods_notebook_image_name'}"
    fi

    # for the rhods-notebooks project
    ./run_toolbox.py from_config cluster set_project_annotation --prefix sutest --suffix rhods_notebooks_node_selector --extra "$dedicated"
    ./run_toolbox.py from_config cluster set_project_annotation --prefix sutest --suffix rhods_notebooks_toleration --extra "$dedicated"
}

capture_environment() {
    switch_sutest_cluster
    ./run_toolbox.py rhods capture_state > /dev/null || true
    ./run_toolbox.py cluster capture_environment > /dev/null || true

    switch_driver_cluster
    ./run_toolbox.py cluster capture_environment > /dev/null || true
}

prepare_ci() {
    cluster_helpers::connect_sutest_cluster

    trap "set +e; sutest_cleanup; driver_cleanup; exit 1" ERR
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

    if [[ "${JOB_NAME_SAFE:-}" == "notebooks-light" ]]; then
        local user_count=$(get_config tests.notebooks.users.count)
        local light_test_user_count=$(get_config 'ci_presets.notebooks_light["tests.notebooks.users.count"]')
        if [[ "$user_count" -gt "$light_test_user_count" ]]; then
            _error "Job '$JOB_NAME_SAFE' shouldn't run with more than $light_test_user_count. Found $user_count."
            exit 1 # shouldn't be reached, but just to be 100% sure.
        fi
    fi

    prepare_sutest_cluster
    prepare_driver_cluster

    process_ctrl::wait_bg_processes

    sutest_wait_rhods_launch
}

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

run_normal_tests_and_plots() {
    local BASE_ARTIFACT_DIR="$ARTIFACT_DIR"

    local test_flavor=$(get_config tests.notebooks.test_flavor)

    local test_failed=0
    local plot_failed=0
    local test_runs=$(get_config tests.notebooks.repeat)

    for idx in $(seq "$test_runs"); do
        if [[ "$test_runs" != 1 ]]; then
            export ARTIFACT_DIR="$BASE_ARTIFACT_DIR/$(printf "%03d" $idx)__test_run"
        fi

        mkdir -p "$ARTIFACT_DIR"
        local pr_file="$BASE_ARTIFACT_DIR"/pull_request.json
        local pr_comment_file="$BASE_ARTIFACT_DIR"/pull_request-comments.json
        for f in "$pr_file" "$pr_comment_file"; do
            [[ -f "$f" ]] && cp "$f" "$ARTIFACT_DIR" || true
        done

        run_test "$idx" && test_failed=0 || test_failed=1

        generate_plots || plot_failed=1

        if [[ "$test_failed" == 1 ]]; then
            break
        fi
    done

    if [[ "$plot_failed" == 1 ]]; then
        return "$plot_failed"
    fi

    return "$test_failed"

}

run_locust_test() {
    switch_driver_cluster
    ./run_toolbox.py from_config rhods notebook_locust_scale_test

    local last_test_dir=$(printf "%s\n" "$ARTIFACT_DIR"/*__*/ | tail -1)
    set_config matbench.test_directory "$last_test_dir"
}

run_single_notebook_test() {
    switch_sutest_cluster # should have only one cluster for this test

    local failed=0

    local namespace=$(get_command_arg namespace rhods benchmark_notebook_performance)
    local toleration_key=$(get_config clusters.driver.compute.machineset.taint.key)

    local use_rhods=$(get_config tests.notebooks.notebook_performance.use_rhods)
    local notebook_performance_tests=$(get_config tests.notebooks.notebook_performance.tests[])
    for notebook_performance_test in $(echo "$notebook_performance_tests" | jq --compact-output); do
        local imagestream=$(echo "$notebook_performance_test" | jq -r .imagestream)
        local notebook_directory=$(echo "$notebook_performance_test" | jq -r .ipynb.uploaded_directory)
        local notebook_filename=$(echo "$notebook_performance_test" | jq -r .ipynb.notebook_filename)
        local instance_types=$(echo "$notebook_performance_test" | jq -r .instance_types[])

        for instance_type in $instance_types; do
            if ! test_config clusters.sutest.is_metal; then
               local machineset_name=$(get_command_arg name cluster set_scale --suffix notebook-performance)
               oc delete "machineset/$machineset_name" \
                  -n openshift-machine-api \
                  --ignore-not-found

               ./run_toolbox.py from_config cluster set_scale \
                                --suffix notebook-performance \
                                --extra "{instance_type:'$instance_type'}"
            fi

            for benchmark in $(echo "$notebook_performance_test" | jq .benchmarks[] --compact-output); do
                local benchmark_name=$(echo "$benchmark" | jq -r .name)

                local benchmark_repeat=$(echo "$benchmark" | jq -r .repeat)
                local benchmark_number=$(echo "$benchmark" | jq -r .number)

                if ! ./run_toolbox.py rhods benchmark_notebook_performance \
                     --imagestream "$imagestream" \
                     --namespace "$namespace" \
                     --use_rhods "$use_rhods" \
                     --notebook_directory "$notebook_directory" \
                     --notebook_filename "$notebook_filename" \
                     --benchmark_name "$benchmark_name" \
                     --benchmark_repeat "$benchmark_repeat" \
                     --benchmark_number "$benchmark_number" \
                   ;
                then
                    failed=$((failed + 1)) # run through all the tests, even in case of a failure
                fi

                local last_test_dir=$(printf "%s\n" "$ARTIFACT_DIR"/*__*/ | tail -1)
                cp  "$CI_ARTIFACTS_FROM_CONFIG_FILE" "$last_test_dir/config.yaml" || true
                cat <<EOF > "$last_test_dir/settings.instance_type" || true
instance_type=$instance_type
EOF
            done
        done
    done

    set_config matbench.test_directory "$ARTIFACT_DIR"

    return $failed
}

run_gating_tests_and_plots() {
    local BASE_ARTIFACT_DIR="$ARTIFACT_DIR"

    do_cleanup() {
        sutest_cleanup_rhods
    }

    cp "$CI_ARTIFACTS_FROM_CONFIG_FILE" "$ARTIFACT_DIR/config.base.yaml"
    local test_idx=0
    local failed=0

    do_cleanup

    for preset in $(get_config tests.notebooks.gating_tests[])
    do
        test_idx=$((test_idx + 1)) # start at 1, 0 is prepare_steps

        # Wait a few minutes if this isn't the first test
        if [[ $test_idx -ne 1 ]]; then
            local WAIT_TIME=5m
            echo "Waiting $WAIT_TIME for the cluster to cool down before running the next test."
            sleep 5m
        fi

        # restore the initial configuration
        cp "$BASE_ARTIFACT_DIR/config.base.yaml" "$CI_ARTIFACTS_FROM_CONFIG_FILE"

        apply_preset "$preset"

        export ARTIFACT_DIR="$BASE_ARTIFACT_DIR/000_prepare_steps/$(printf "%03d" $test_idx)__prepare_${preset}"

        if ! prepare; then
            ARTIFACT_DIR="$BASE_ARTIFACT_DIR" _warning "Gating preset '$preset' preparation failed :/"
            failed=1

            do_cleanup

            continue
        fi

        export ARTIFACT_DIR="$BASE_ARTIFACT_DIR/$(printf "%03d" $test_idx)_$preset"
        if ! run_normal_tests_and_plots; then
            ARTIFACT_DIR="$BASE_ARTIFACT_DIR" _warning "Gating preset '$preset' test failed :/"
            failed=1
        fi

        do_cleanup
    done

    export ARTIFACT_DIR="$BASE_ARTIFACT_DIR"
    if [[ "$failed" == 1 ]]; then
        _warning "Gating test failed :/"
    fi

    return $failed
}

driver_cleanup() {
    switch_driver_cluster

    local user_count=$(get_config tests.notebooks.users.count)

    skip_threshold=$(get_config tests.notebooks.cleanup.skip_if_le_than_users)
    if [[ "$user_count" -le "$skip_threshold" ]]; then
        _info "Skip cluster cleanup (less that $skip_threshold users)"
        return
    fi

    if ! test_config clusters.sutest.is_metal; then
       ./run_toolbox.py from_config cluster set_scale --prefix "driver" --suffix "cleanup" > /dev/null
    fi

    if test_config tests.notebooks.cleanup.cleanup_driver_on_exit; then

        ods_ci_test_namespace=$(get_config tests.notebooks.namespace)
        statesignal_redis_namespace=$(get_command_arg namespace cluster deploy_redis_server)
        nginx_notebook_namespace=$(get_command_arg namespace cluster deploy_nginx_server)
        oc delete namespace --ignore-not-found \
           "$ods_ci_test_namespace" \
           "$statesignal_redis_namespace" \
           "$nginx_notebook_namespace"
    fi
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
    elif ! test_config clusters.sutest.is_metal; then
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

    if ! ./run_toolbox.py from_config rhods cleanup_notebooks > /dev/null; then
        _warning "rhods notebook cleanup failed :("
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

generate_plots() {
    local artifact_next_dir_idx=$(ls "${ARTIFACT_DIR}/" | grep __ | wc -l)
    local plots_dirname="$(printf '%03d' "$artifact_next_dir_idx")__plots"
    local plots_artifact_dir="$ARTIFACT_DIR/$plots_dirname"

    local test_dir=$(get_config matbench.test_directory)

    if [[ "$test_dir" == null ]]; then
        _error "generate_plots: matbench.test_directory should be set."
    fi

    mkdir -p "$plots_artifact_dir"

    if ARTIFACT_DIR="$plots_artifact_dir" \
                   ./testing/ods/generate_matrix-benchmarking.sh \
                   from_dir "$test_dir" \
                       > "$plots_artifact_dir/build-log.txt" 2>&1;
    then
        echo "MatrixBenchmarkings plots successfully generated."
    else
        local errcode=$?
        _warning "MatrixBenchmarkings plots generated failed. See logs in $ARTIFACT_DIR/$plots_dirname/build-log.txt"
        return $errcode
    fi
}

connect_ci() {
    "$TESTING_ODS_DIR/ci_init_configure.sh"

    if [[ "${JOB_NAME_SAFE:-}" == "notebooks-light" ]]; then
        local LIGHT_PROFILE="notebooks_light"
        # running with a CI-provided cluster
        _info "Running '$JOB_NAME_SAFE' test, applying '$LIGHT_PROFILE' extra preset."
        set_config PR_POSITIONAL_ARG_EXTRA_LIGHT "$LIGHT_PROFILE"
    fi

    if [[ $(oc whoami --show-console) == *"bm.example.com"* ]]; then
        local METAL_PROFILE="metal"

        echo "Bare-metal environment detected, applying the 'metal' profile".
        set_config PR_POSITIONAL_ARG_EXTRA_METAL "$METAL_PROFILE"
    fi

    set_presets_from_pr_args

    bash "$TESTING_ODS_DIR/configure_set_presets.sh"
    # ^^^ applies the presets
    # vvv overrides the presets, if necessary
    bash "$TESTING_ODS_DIR/configure_overrides.sh"

    if [[ "${CONFIG_DEST_DIR:-}" ]]; then
        echo "Using CONFIG_DEST_DIR=$CONFIG_DEST_DIR ..."

    elif [[ "${SHARED_DIR:-}" ]]; then
        echo "Using CONFIG_DEST_DIR=\$SHARED_DIR=$SHARED_DIR ..."
        CONFIG_DEST_DIR=$SHARED_DIR

    else
        _error "CONFIG_DEST_DIR or SHARED_DIR must be set ..."
    fi

    KUBECONFIG_DRIVER="${CONFIG_DEST_DIR}/driver_kubeconfig" # cluster driving the test
    KUBECONFIG_SUTEST="${CONFIG_DEST_DIR}/sutest_kubeconfig" # system under test
}

run_tests_and_plots() {
    local test_flavor=$(get_config tests.notebooks.test_flavor)

    sutest_cleanup_rhods

    if [[ "$test_flavor" == "gating" ]]; then
        run_gating_tests_and_plots
    else
        run_normal_tests_and_plots
    fi
}

run_test() {
    local repeat_idx=${1:-}

    local test_flavor=$(get_config tests.notebooks.test_flavor)
    if [[ "$repeat_idx" ]]; then
        mkdir -p "$ARTIFACT_DIR"
        echo "repeat=$repeat_idx" > "$ARTIFACT_DIR/settings.repeat"
    fi
    if [[ "$test_flavor" == "ods-ci" ]]; then
        run_ods_ci_test || return 1
    elif [[ "$test_flavor" == "locust" ]]; then
        run_locust_test "$repeat_idx" || return 1
    elif [[ "$test_flavor" == "notebook-performance" ]]; then
        run_single_notebook_test "$repeat_idx" || return 1
    elif [[ "$test_flavor" == "gating" ]]; then
        # 'gating' testing is handled higher in the call stack, before the 'repeat' (in run_gating_tests_and_plots)
        _error "Test flavor cannot be '$test_flavor' in function run_test."
    else
        _error "Unknown test flavor: $test_flavor"
    fi

    ./run_toolbox.py rhods capture_state > /dev/null || true
}

apply_presets_from_args() {
    cp "$CI_ARTIFACTS_FROM_CONFIG_FILE" "$ARTIFACT_DIR" || true
    export CI_ARTIFACTS_FROM_CONFIG_FILE="$ARTIFACT_DIR/$(basename "$CI_ARTIFACTS_FROM_CONFIG_FILE")"

    while [[ "${1:-}" ]]; do
        apply_preset "$1"
        shift
    done
}

export_to_s3() {
    local ts_id=${1:-$(date "+%Y%M%d_%H%M")}
    local run_identifier=${2:-default}

    export AWS_SHARED_CREDENTIALS_FILE="${PSAP_ODS_SECRET_PATH:-}/.awscred"
    local bucket_name=$(get_config "export_to_s3.bucket_name")

    local dest="s3://$bucket_name/local-ci/$ts_id/$run_identifier"
    echo "Pushing to '$dest'"
    aws s3 cp "$ARTIFACT_DIR" "$dest" --recursive --acl public-read
}

# ---

main() {
    process_ctrl__finalizers+=("process_ctrl::kill_bg_processes")

    if [[ "$(get_config clusters.create.type)" == "customer" ]]; then
        case ${action} in
            "prepare_ci")
                exec "$TESTING_ODS_DIR/run_notebook_scale_test_on_customer.sh" prepare
                ;;
            "test_ci")
                exec "$TESTING_ODS_DIR/run_notebook_scale_test_on_customer.sh" test
                ;;
        esac

        return 1
    fi

    action=${1:-}
    shift || true

    case ${action} in
        "connect_ci")
            connect_ci
            return 0
            ;;
        "prepare_ci")
            connect_ci

            prepare_ci

            prepare

            process_ctrl::wait_bg_processes
            return 0
            ;;
        "test_ci")
            connect_ci
            local BASE_ARTIFACT_DIR=$ARTIFACT_DIR

            process_ctrl__finalizers+=("export ARTIFACT_DIR='$BASE_ARTIFACT_DIR/999_teardown'") # switch to the 'teardown' artifacts directory
            process_ctrl__finalizers+=("capture_environment")
            process_ctrl__finalizers+=("sutest_cleanup")
            process_ctrl__finalizers+=("driver_cleanup")

            run_tests_and_plots
            return 0
            ;;
        "prepare")
            prepare
            return 0
            ;;
        "deploy_rhods")
            prepare_sutest_deploy_rhods
            process_ctrl::wait_bg_processes
            return 0
            ;;
        "wait_rhods")
            sutest_wait_rhods_launch
            process_ctrl::wait_bg_processes
            return 0
            ;;
        "deploy_ldap")
            prepare_sutest_deploy_ldap
            process_ctrl::wait_bg_processes
            return 0
            ;;
        "undeploy_ldap")
            sutest_cleanup_ldap
            return 0
            ;;
        "prepare_driver_cluster")
            apply_presets_from_args "$@"

            prepare_driver_cluster
            process_ctrl::wait_bg_processes
            return 0
            ;;
        "run_test_and_plot")
            local failed=0
            export CI_ARTIFACTS_CAPTURE_PROM_DB=1

            apply_presets_from_args "$@"

            run_test || failed=1

            generate_plots || failed=1

            return $failed
            ;;
        "run_tests_and_plots")

            apply_presets_from_args "$@"

            run_tests_and_plots
            return 0
            ;;
        "run_test")

            apply_presets_from_args "$@"

            run_test
            return 0
            ;;
        "generate_plots")

            apply_presets_from_args "$@"

            generate_plots
            return  0
            ;;
        "generate_plots_from_pr_args")
            export IGNORE_PSAP_ODS_SECRET_PATH=1
            connect_ci

            testing/ods/generate_matrix-benchmarking.sh from_pr_args
            return  0
            ;;
        "cleanup_rhods")
            sutest_cleanup_rhods
            return 0
            ;;
        "prepare_matbench")
            testing/ods/generate_matrix-benchmarking.sh prepare_matbench
            return 0
            ;;
        "rebuild_ods-ci")
            local namespace=$(get_config tests.notebooks.namespace)
            local istag=$(get_command_arg ods_ci_istag rhods notebook_ods_ci_scale_test)
            oc delete istag "$istag" -n "$namespace" --ignore-not-found
            build_and_preload_ods_ci_image
            return 0
            ;;
        "export_to_s3")
            export_to_s3 "$@"

            return 0
            ;;
        "source")
            # file is being sourced by another script
            ;;
        *)
            _error "unknown action: ${action}" "$@"
            ;;
    esac
}

main "$@"
