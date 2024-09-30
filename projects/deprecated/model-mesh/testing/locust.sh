#! /bin/bash

set -o errexit
set -o pipefail
set -o nounset
set -o errtrace
set -x

TESTING_MM_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
TESTING_NOTEBOOKS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )/../notebooks"

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

source "$TESTING_MM_DIR/config.sh"
source "$TESTING_MM_DIR/../utils/logging.sh"
source "$TESTING_MM_DIR/../process_ctrl.sh"
source "$TESTING_NOTEBOOKS_DIR/configure.sh"
source "$TESTING_NOTEBOOKS_DIR/cluster_helpers.sh"
export CI_ARTIFACTS_FROM_CONFIG_FILE=${TESTING_MM_DIR}/config.yaml
export CI_ARTIFACTS_FROM_COMMAND_ARGS_FILE=${TESTING_MM_DIR}/command_args.yml.j2

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

    local loadtest_namespace=$(get_config tests.model_mesh.namespace)

    oc create namespace "$loadtest_namespace" -oyaml --dry-run=client | oc apply -f-

    build_and_preload_artifacts_exporter_image() {
        ./run_toolbox.py from_config cluster build_push_image --suffix artifacts-exporter
        ./run_toolbox.py from_config cluster preload_image --suffix artifacts-exporter
    }

    build_and_preload_api_scale_test_image() {
        ./run_toolbox.py from_config cluster build_push_image --suffix locust-scale-test
        ./run_toolbox.py from_config cluster preload_image --suffix locust-scale-test
    }

    process_ctrl::run_in_bg build_and_preload_artifacts_exporter_image
    process_ctrl::run_in_bg build_and_preload_api_scale_test_image

    process_ctrl::run_in_bg ./run_toolbox.py from_config server deploy_minio_s3_server
}

prepare_sutest_cluster() {
    switch_sutest_cluster

    if [[ "$SCALE_INSTANCES" -eq 0 ]]
    then
        ./run_toolbox.py cluster set-scale ${INSTANCE_TYPE} ${INSTANCE_COUNT}
    fi
}

capture_environment() {
    switch_sutest_cluster
    ./run_toolbox.py notebooks capture_state > /dev/null || true
    ./run_toolbox.py cluster capture_environment > /dev/null || true

    switch_driver_cluster
    ./run_toolbox.py cluster capture_environment > /dev/null || true
}

prepare_ci() {
    cluster_helpers::connect_sutest_cluster
}

prepare() {
    prepare_sutest_cluster
    prepare_driver_cluster

    process_ctrl::wait_bg_processes
}

run_locust_test() {
    switch_driver_cluster

    # to be customized
    ./run_toolbox.py from_config rhods notebook_api_scale_test \
                     --extra "{sut_cluster_kubeconfig: '$KUBECONFIG_SUTEST'}"
}

generate_plots() {
    local BASE_ARTIFACT_DIR="$ARTIFACT_DIR"
    local PLOT_ARTIFACT_DIR="$ARTIFACT_DIR/plotting"
    mkdir "$PLOT_ARTIFACT_DIR"
    if ARTIFACT_DIR="$PLOT_ARTIFACT_DIR" \
                   ./testing/notebooks/generate_matrix-benchmarking.sh \
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
    "$TESTING_UTILS_DIR/ci_init_configure.sh"

    if [[ "${CONFIG_DEST_DIR:-}" ]]; then
        echo "Using CONFIG_DEST_DIR=$CONFIG_DEST_DIR ..."

    elif [[ "${SHARED_DIR:-}" ]]; then
        echo "Using CONFIG_DEST_DIR=\$SHARED_DIR=$SHARED_DIR ..."
        CONFIG_DEST_DIR=$SHARED_DIR

    else
        _error "CONFIG_DEST_DIR or SHARED_DIR must be set ..."
    fi

    KUBECONFIG_DRIVER="${CONFIG_DEST_DIR}/driver_kubeconfig" # cluster driving the test
    if [[ ! -f "$KUBECONFIG_DRIVER" ]]; then
        KUBECONFIG_DRIVER=$KUBECONFIG
    fi
    KUBECONFIG_SUTEST="${CONFIG_DEST_DIR}/sutest_kubeconfig" # system under test
    if [[ ! -f "$KUBECONFIG_SUTEST" ]]; then
        KUBECONFIG_SUTEST=$KUBECONFIG
    fi
}

test_ci() {
    run_one_test
}

run_one_test() {
    run_locust_test
}

# ---

main() {
    process_ctrl__finalizers+=("process_ctrl::kill_bg_processes")

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

            test_ci
            return 0
            ;;
        "prepare")
            prepare
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
        *)
            _error "unknown action: ${action}" "$@"
            ;;
    esac
}

main "$@"
