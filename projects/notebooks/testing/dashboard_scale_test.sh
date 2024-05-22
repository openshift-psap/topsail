#! /bin/bash

run_dashboard_scale_test() {
    switch_driver_cluster

    failed=0

    ./run_toolbox.py from_config notebooks dashboard_scale_test || failed=1

    # quick access to these files
    local last_test_dir=$(printf "%s\n" "$ARTIFACT_DIR"/*__*/ | tail -1)
    cp "$last_test_dir/"{failed_tests,success_count} "$ARTIFACT_DIR" 2>/dev/null 2>/dev/null || true

    cp  "$CI_ARTIFACTS_FROM_CONFIG_FILE" "$last_test_dir/config.yaml" || true
    set_config matbench.test_directory "$last_test_dir"

    return $failed
}
