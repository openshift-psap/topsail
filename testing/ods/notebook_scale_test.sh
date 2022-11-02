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

    export ARTIFACT_DIR="/tmp/ci-artifacts_$(date +%Y%m%d)"
    mkdir -p "$ARTIFACT_DIR"

    echo "Using ARTIFACT_DIR=$ARTIFACT_DIR as default artifacts directory."
else
    echo "Using ARTIFACT_DIR=$ARTIFACT_DIR."
fi

source "$TESTING_ODS_DIR/../_logging.sh"
source "$TESTING_ODS_DIR/../process_ctrl.sh"
source "$TESTING_ODS_DIR/configure.sh"
source "$TESTING_ODS_DIR/cluster_helpers.sh"

KUBECONFIG_DRIVER="${KUBECONFIG_DRIVER:-$KUBECONFIG}" # cluster driving the test
KUBECONFIG_SUTEST="${KUBECONFIG_SUTEST:-$KUBECONFIG}" # system under test


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

prepare_driver_cluster() {
    switch_cluster driver

    prepare_driver_scale_cluster

    local loadtest_namespace=$(get_config tests.notebooks.namespace)

    oc create namespace "$loadtest_namespace" -oyaml --dry-run=client | oc apply -f-

    local driver_taint_key=$(get_config clusters.driver.compute.machineset.taint.key)
    local driver_taint_value=$(get_config clusters.driver.compute.machineset.taint.value)
    local driver_taint_effect=$(get_config clusters.driver.compute.machineset.taint.effect)
    oc annotate namespace/"$loadtest_namespace" --overwrite \
       "openshift.io/node-selector=$driver_taint_key=$driver_taint_value"
    oc annotate namespace/"$loadtest_namespace" --overwrite \
       'scheduler.alpha.kubernetes.io/defaultTolerations=[{"operator": "Exists", "effect": "'$driver_taint_effect'", "key": "'$driver_taint_key'"}]'


    build_and_preload_user_scale_test_image() {
        process_ctrl::retry 5 30s \
                            ./run_toolbox.py from_config utils build_push_image --suffix user-scale-test
        ./run_toolbox.py from_config cluster preload_image --suffix user-scale-test
    }

    build_and_preload_artifacts_exporter_image() {
        ./run_toolbox.py from_config utils build_push_image --suffix artifacts-exporter
        ./run_toolbox.py from_config cluster preload_image --suffix artifacts-exporter
    }

    build_and_preload_api_scale_test_image() {
        ./run_toolbox.py from_config utils build_push_image --suffix api-scale-test
        ./run_toolbox.py from_config cluster preload_image --suffix api-scale-test
    }

    process_ctrl::run_in_bg build_and_preload_user_scale_test_image
    process_ctrl::run_in_bg build_and_preload_artifacts_exporter_image
    process_ctrl::run_in_bg build_and_preload_api_scale_test_image

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

    local compute_nodes_count=$(get_config clusters.driver.compute.machineset.count)
    if [[ "$compute_nodes_count" == "null" ]]; then
        compute_nodes_count=$(cluster_helpers::get_compute_node_count driver)
    fi

    local driver_taint_key=$(get_config clusters.driver.compute.machineset.taint.key)
    local driver_taint_value=$(get_config clusters.driver.compute.machineset.taint.value)
    local driver_taint_effect=$(get_config clusters.driver.compute.machineset.taint.effect)
    local driver_taint="$driver_taint_key=$driver_taint_value:$driver_taint_effect"

    if test_config clusters.sutest.is_managed; then
        local managed_cluster_name=$(get_config clusters.sutest.managed.name)
        local machinepool_name=$(get_config clusters.driver.compute.machineset_name)

        if test_config clusters.sutest.managed.is_ocm; then
            local compute_nodes_type=$(get_config clusters.create.ocm.compute.type)
            ocm create machinepool \
                --cluster "$managed_cluster_name" \
                --instance-type "$compute_nodes_type" \
                "$machinepool_name" \
                --replicas "$compute_nodes_count" \
                --taints "$driver_taint"
        elif test_config clusters.sutest.managed.is_rosa; then
            _error "prepare_driver_scale_cluster not supported with ROSA"
        fi
    else
        ./run_toolbox.py from_config cluster set_scale --prefix="driver" \
                         --extra "{scale: $compute_nodes_count}"
    fi
}

prepare_sutest_scale_cluster() {
    local cluster_role=sutest

    switch_sutest_cluster

    local compute_nodes_count=$(get_config clusters.sutest.compute.machineset.count)
    if [[ "$compute_nodes_count" == "null" ]]; then
        compute_nodes_count=$(cluster_helpers::get_compute_node_count sutest)
    fi

    local sutest_taint_key=$(get_config clusters.sutest.compute.machineset.taint.key)
    local sutest_taint_value=$(get_config clusters.sutest.compute.machineset.taint.value)
    local sutest_taint_effect=$(get_config clusters.sutest.compute.machineset.taint.effect)
    local sutest_taint="$sutest_taint_key=$sutest_taint_value:$sutest_taint_effect"
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
        local managed_cluster_name=$(get_config clusters.sutest.managed.name)
        if test_config clusters.sutest.managed.is_ocm; then
            local compute_nodes_type=$(get_config clusters.create.ocm.compute.type)
            ocm create machinepool "$(get_config clusters.sutest.compute.machineset_name)" \
                --cluster "$managed_cluster_name" \
                --instance-type "$compute_nodes_type" \
                --taints "$sutest_taint" \
                $specific_options
        elif test_config clusters.sutest.managed.is_rosa; then
            _error "prepare_sutest_scale_cluster not supported with rosa"
        fi
    else
        ./run_toolbox.py from_config cluster set_scale --prefix="sutest" \
                         --extra "{scale: $compute_nodes_count}"

        if test_config clusters.sutest.compute.autoscaling.enabled; then
            oc apply -f testing/ods/autoscaling/clusterautoscaler.yaml

            local machineset_name=$(get_config clusters.sutest.machineset_name)
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
        local email=$(get_config rhods.addon.email)
        process_ctrl::run_in_bg \
            ./run_toolbox.py from_config rhods deploy_addon "$managed_cluster_name" "$email"
    fi
}

prepare_ocp_sutest_deploy_rhods() {
    switch_sutest_cluster

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
    if test_config "$NB_SIZE_CONFIG_KEY.enabled" ]]; then
        local name=$(get_config $NB_SIZE_CONFIG_KEY.name)
        local cpu=$(get_config $NB_SIZE_CONFIG_KEY.cpu)
        local mem=$(get_config $NB_SIZE_CONFIG_KEY.mem_gi)

        oc get odhdashboardconfig/odh-dashboard-config -n redhat-ods-applications -ojson \
            | jq '.spec.notebookSizes = [{"name": "'$name'", "resources": { "limits":{"cpu":"'$cpu'", "memory":"'$mem'Gi"}, "requests":{"cpu":"'$cpu'", "memory":"'$mem'Gi"}}}]' \
            | oc apply -f-
    fi

}

sutest_wait_rhods_launch() {
    switch_sutest_cluster

    local customize_key=rhods.notebooks.customize.enabled

    if test_config "$customize_key"; then
        sutest_customize_rhods_before_wait
    fi

    ./run_toolbox.py rhods wait_ods

    if test_config "$customize_key"; then
        sutest_customize_rhods_after_wait

        ./run_toolbox.py rhods wait_ods
    fi


    if test_config clusters.sutest.compute.autoscaling.enable; then
        local rhods_notebook_image_name=$(get_config tests.notebooks.notebook.image_name)
        local rhods_notebook_image_tag=$(oc get istag -n redhat-ods-applications -oname \
                                       | cut -d/ -f2 | grep "$rhods_notebook_image_name" | cut -d: -f2)

        # preload the image only if auto-scaling is disabled
        notebook_image="image-registry.openshift-image-registry.svc:5000/redhat-ods-applications/$rhods_notebook_image_name:$rhods_notebook_image_tag"
        ./run_toolbox.py from_config cluster preload_image --suffix "notebook" \
                         --extra "{image:'$notebook_image'}"
    fi

    local sutest_taint_key=$(get_config clusters.sutest.compute.machineset.taint.key)
    local sutest_taint_value=$(get_config clusters.sutest.compute.machineset.taint.value)
    local sutest_taint_effect=$(get_config clusters.sutest.compute.machineset.taint.effect)

    oc annotate namespace/rhods-notebooks --overwrite \
       "openshift.io/node-selector=$sutest_taint_key=$sutest_taint_value"
    oc annotate namespace/rhods-notebooks --overwrite \
       'scheduler.alpha.kubernetes.io/defaultTolerations=[{"operator": "Exists", "effect": "'$sutest_taint_effect'", "key": "'$sutest_taint_key'"}]'
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

prepare() {
    prepare_sutest_cluster
    prepare_driver_cluster

    process_ctrl::wait_bg_processes

    sutest_wait_rhods_launch
}

run_user_level_test() {
    switch_driver_cluster

    local nginx_server=$(get_command_arg __server_name cluster deploy_nginx_server)
    local nginx_hostname=$(oc whoami --show-server | sed "s/api/$nginx_server.apps/g" | awk -F ":" '{print $2}' | sed s,//,,g)

    local notebook_name=$(get_config tests.notebooks.ipynb.notebook_filename)
    local notebook_url="http://$nginx_hostname/$notebook_name"
    ./run_toolbox.py from_config rhods notebook_ux_e2e_scale_test \
                     --extra "{notebook_url: '$notebook_url', sut_cluster_kubeconfig: '$KUBECONFIG_SUTEST'}"
}

run_user_level_tests() {
    local BASE_ARTIFACT_DIR="$ARTIFACT_DIR"

    local test_failed=0
    local plot_failed=0
    local test_runs=$(get_config tests.notebooks.repeat)
    for idx in $(seq "$test_runs"); do
        export ARTIFACT_DIR="$BASE_ARTIFACT_DIR/$(printf "%03d" $idx)_test_run"

        mkdir -p "$ARTIFACT_DIR"
        local pr_file="$BASE_ARTIFACT_DIR"/pull_request.json
        local pr_comment_file="$BASE_ARTIFACT_DIR"/pull_request-comments.json
        for f in "$pr_file" "$pr_comment_file"; do
            [[ -f "$f" ]] && cp "$f" "$ARTIFACT_DIR"
        done

        run_user_level_test && test_failed=0 || test_failed=1
        # quick access to these files
        cp "$ARTIFACT_DIR"/*__driver_rhods__notebook_ux_e2e_scale_test/{failed_tests,success_count} "$ARTIFACT_DIR" 2>/dev/null || true
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

run_api_level_test() {
    switch_driver_cluster
    ./run_toolbox.py from_config rhods notebook_api_scale_test
}

driver_cleanup() {
    switch_driver_cluster

    local user_count=$(get_config tests.notebooks.users.count)

    skip_threshold=$(get_config tests.notebooks.cleanup.skip_if_le_than_users)
    if [[ "$user_count" -le "$skip_threshold" ]]; then
        _info "Skip cluster cleanup (less that $skip_threshold users)"
        return
    fi

    ./run_toolbox.py from_config cluster set_scale --prefix "driver" --suffix "cleanup" > /dev/null

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
    else
        ./run_toolbox.py from_config cluster set_scale --prefix "sutest" --suffix "cleanup" > /dev/null
    fi
}

sutest_cleanup_ldap() {
    switch_sutest_cluster

    if ! ./run_toolbox.py from_config rhods cleanup_notebooks > /dev/null; then
        _warning "rhods notebook cleanup failed :("
    fi

    if oc get cm/keep-cluster -n default 2>/dev/null; then
        _info "cm/keep-cluster found, not undeploying LDAP."
        return
    fi

    ./run_toolbox.py from_config cluster undeploy_ldap  > /dev/null
}

generate_plots() {
    local BASE_ARTIFACT_DIR="$ARTIFACT_DIR"
    local PLOT_ARTIFACT_DIR="$ARTIFACT_DIR/plotting"
    mkdir "$PLOT_ARTIFACT_DIR"
    if ARTIFACT_DIR="$PLOT_ARTIFACT_DIR" \
                   ./testing/ods/generate_matrix-benchmarking.sh \
                   from_dir "$BASE_ARTIFACT_DIR" \
                       > "$PLOT_ARTIFACT_DIR/build-log.txt" 2>&1;
    then
        echo "MatrixBenchmarkings plots successfully generated."
    else
        local errcode=$?
        _warning "MatrixBenchmarkings plots generated failed. See logs in \$ARTIFACT_DIR/plotting/build-log.txt"
        return $errcode
    fi
}

connect_ci() {
    "$TESTING_ODS_DIR/ci_init_configure.sh"

    if [[ "${CONFIG_DEST_DIR:-}" ]]; then
        echo "Using CONFIG_DEST_DIR=$CONFIG_DEST_DIR ..."

    elif [[ "${SHARED_DIR:-}" ]]; then
        echo "Using CONFIG_DEST_DIR=\$SHARED_DIR=$SHARED_DIR ..."
        CONFIG_DEST_DIR=$SHARED_DIR

    else
        _error "CONFIG_DEST_DIR or SHARED_DIR must be set ..."
    fi

    KUBECONFIG_DRIVER="${KUBECONFIG_DRIVER:-${CONFIG_DEST_DIR}/driver_kubeconfig}" # cluster driving the test
    KUBECONFIG_SUTEST="${KUBECONFIG_SUTEST:-${CONFIG_DEST_DIR}/sutest_kubeconfig}" # system under test
}

test_ci() {

    local test_flavor=$(get_config tests.notebooks.flavor_to_run)
    if [[ "$test_flavor" == "user-level" ]]; then
        run_user_level_tests
    elif [[ "$test_flavor" == "api-level" ]]; then
        run_api_level_test
    else
        _error "Unknown test flavor: $test_flavor"
    fi
}

run_one_test() {
    local test_flavor=$(get_config tests.notebooks.flavor_to_run)
    if [[ "$test_flavor" == "user-level" ]]; then
        run_user_level_test
    elif [[ "$test_flavor" == "api-level" ]]; then
        run_api_level_test
    else
        _error "Unknown test flavor: $test_flavor"
    fi
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

    case ${action} in
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

            test_ci
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
            prepare_driver_cluster
            process_ctrl::wait_bg_processes
            return 0
            ;;
        "run_test_and_plot")
            run_one_test
            generate_plots
            return 0
            ;;
        "run_test")
            run_one_test
            return 0
            ;;
        "generate_plots")
            generate_plots
            return  0
            ;;
        "generate_plots_from_pr_args")
            testing/ods/generate_matrix-benchmarking.sh from_pr_args
            return  0
            ;;
        "prepare_matbench")
            testing/ods/generate_matrix-benchmarking.sh prepare_matbench
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
