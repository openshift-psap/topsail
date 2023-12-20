#! /bin/bash

set -o errexit
set -o pipefail
set -o nounset
set -o errtrace
set -x

TESTING_NOTEBOOKS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
TOPSAIL_DIR="$(cd "$TESTING_NOTEBOOKS_DIR/../../.." >/dev/null 2>&1 && pwd )"
TESTING_UTILS_DIR="$TOPSAIL_DIR/testing/utils"

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

source "$TESTING_UTILS_DIR/logging.sh"
source "$TESTING_UTILS_DIR/process_ctrl.sh"
source "$TESTING_NOTEBOOKS_DIR/configure.sh"
source "$TESTING_NOTEBOOKS_DIR/cluster_helpers.sh"

if [[ "${OPENSHIFT_CI:-}" == true && "${JOB_NAME_SAFE:-}" == "light" ]]; then
    cp "$KUBECONFIG" "${SHARED_DIR}/driver_kubeconfig"
    cp "$KUBECONFIG" "${SHARED_DIR}/sutest_kubeconfig"
fi

KUBECONFIG_DRIVER="${KUBECONFIG_DRIVER:-${KUBECONFIG:-}}" # cluster driving the test
KUBECONFIG_SUTEST="${KUBECONFIG_SUTEST:-${KUBECONFIG:-}}" # system under test

# ---

source "$TESTING_NOTEBOOKS_DIR"/prepare_common.sh
source "$TESTING_NOTEBOOKS_DIR"/prepare_driver.sh
source "$TESTING_NOTEBOOKS_DIR"/prepare_sutest.sh
source "$TESTING_NOTEBOOKS_DIR"/scale_test_ods_ci.sh
source "$TESTING_NOTEBOOKS_DIR"/scale_test_run_tests.sh
source "$TESTING_NOTEBOOKS_DIR"/single_notebook_performance_test.sh

# ---

connect_ci() {
    "$TESTING_UTILS_DIR/ci_init_configure.sh"

    if [[ "${JOB_NAME_SAFE:-}" == "light" ||  "${JOB_NAME_SAFE:-}" == *"-light" ]]; then
        local LIGHT_PROFILE="light"
        # running a light test (usually in a CI-provided cluster)
        _info "Running '$JOB_NAME_SAFE' test, applying '$LIGHT_PROFILE' extra preset."
        set_config PR_POSITIONAL_ARG_EXTRA_LIGHT "$LIGHT_PROFILE"
    fi

    if [[ $(oc whoami --show-console) == *"bm.example.com"* ]]; then
        local METAL_PROFILE="metal"

        echo "Bare-metal environment detected, applying the 'metal' profile".
        set_config PR_POSITIONAL_ARG_EXTRA_METAL "$METAL_PROFILE"
    fi

    if [[ "${JOB_NAME_SAFE:-}" != "plot" ]]; then
        set_presets_from_pr_args
    fi

    bash "$TESTING_UTILS_DIR/configure_set_presets.sh"
    # ^^^ applies the presets
    # vvv overrides the presets, if necessary
    bash "$TESTING_UTILS_DIR/configure_overrides.sh"

    if [[ "${OPENSHIFT_CI:-}" == true ]]; then
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
    fi
}

show_help_and_exit() {
    if ! test_config tests.show_help; then
        return
    fi

    echo "Available presets:"
    get_config ci_presets | jq 'to_entries | .[] | "- " + .key' -r

    exit 0
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
                   "$TESTING_NOTEBOOKS_DIR/generate_matrix-benchmarking.sh" \
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

apply_presets_from_args() {
    cp "$CI_ARTIFACTS_FROM_CONFIG_FILE" "$ARTIFACT_DIR" || true
    export CI_ARTIFACTS_FROM_CONFIG_FILE="$ARTIFACT_DIR/$(basename "$CI_ARTIFACTS_FROM_CONFIG_FILE")"

    while [[ "${1:-}" ]]; do
        apply_preset "$1"
        shift
    done
}

check_failure_flag() {
    if find "$ARTIFACT_DIR" -type f -name FAILURE -exec false {} +; then
        echo "No failure detected"
        exit 0
    fi

    echo "FATAL: failure detected, aborting :/"
    exit 1
}

# ---

main() {
    process_ctrl__finalizers+=("process_ctrl::kill_bg_processes")

    action=${1:-}
    shift || true

    apply_presets_from_args "$@"

    case ${action} in
        "connect_ci")
            connect_ci
            return 0
            ;;
        "prepare_ci")
            connect_ci

            show_help_and_exit

            prepare_ci

            prepare

            process_ctrl::wait_bg_processes
            wait # ensure that there's really no background process
            check_failure_flag

            return 0
            ;;
        "test_ci")
            connect_ci

            show_help_and_exit

            local BASE_ARTIFACT_DIR=$ARTIFACT_DIR

            process_ctrl__finalizers+=("export ARTIFACT_DIR='$BASE_ARTIFACT_DIR/999__teardown'") # switch to the 'teardown' artifacts directory
            process_ctrl__finalizers+=("capture_environment")
            process_ctrl__finalizers+=("sutest_cleanup")
            process_ctrl__finalizers+=("driver_cleanup")

            run_tests_and_plots

            local horreum_test_name=$(get_config matbench.lts.horreum.test_name)
            if [[ "$horreum_test_name" ]]; then
                echo "Saving Horreum test name: $horreum_test_name"
                echo "$horreum_test_name" > $ARTIFACT_DIR/test_name.horreum
            fi

            check_failure_flag

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
            switch_sutest_cluster
            ./run_toolbox.py from_config cluster undeploy_ldap  > /dev/null
            return 0
            ;;
        "prepare_driver_cluster")
            prepare_driver_cluster
            process_ctrl::wait_bg_processes
            return 0
            ;;
        "run_test_and_plot")
            local failed=0
            export CI_ARTIFACTS_CAPTURE_PROM_DB=1

            run_test || failed=1

            generate_plots || failed=1

            return $failed
            ;;
        "run_tests_and_plots")
            run_tests_and_plots
            return 0
            ;;
        "run_test")
            run_test
            return 0
            ;;
        "generate_plots")
            generate_plots
            return  0
            ;;
        "generate_plots_from_pr_args")
            export IGNORE_PSAP_ODS_SECRET_PATH=1
            connect_ci

            "$TESTING_NOTEBOOKS_DIR/generate_matrix-benchmarking.sh" from_pr_args
            return  0
            ;;
        "cleanup_rhods")
            sutest_cleanup_rhods
            return 0
            ;;
        "cleanup_cluster_ci")
            connect_ci

            show_help_and_exit

            ;& # fallthrough
        "cleanup_clusters")
            apply_preset cleanup
            sutest_cleanup
            driver_cleanup

            lab_ci_sutest_cleanup

            return 0
            ;;
        "prepare_matbench")
            "$TESTING_NOTEBOOKS_DIR/generate_matrix-benchmarking.sh" prepare_matbench
            return 0
            ;;
        "rebuild_ods-ci")
            local namespace=$(get_config tests.notebooks.namespace)
            local istag=$(get_command_arg ods_ci_istag rhods notebook_ods_ci_scale_test)
            oc delete istag "$istag" -n "$namespace" --ignore-not-found
            driver_build_and_preload_ods_ci_image
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
