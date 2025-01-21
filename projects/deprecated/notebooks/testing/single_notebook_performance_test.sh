#! /bin/bash

run_single_notebook_tests_run_benchmark_against_imagestream() {
    local notebook_performance_test="$1"
    local benchmark="$2"
    local instance_type="$3"
    local imagestream="$4"
    if [[ "${5:-}" ]]; then
        local imagestream_tag="--imagestream_tag=$5"
    else
        local imagestream_tag=""
    fi

    local notebook_directory=$(echo "$notebook_performance_test" | jq -r .ipynb.uploaded_directory)
    local notebook_filename=$(echo "$notebook_performance_test" | jq -r .ipynb.notebook_filename)

    local benchmark_name=$(echo "$benchmark" | jq -r .name)

    local benchmark_repeat=$(echo "$benchmark" | jq -r .repeat)
    local benchmark_number=$(echo "$benchmark" | jq -r .number)

    if get_config tests.notebooks.notebook_performance.incompatible_images[] | grep "$imagestream" --quiet; then
        _info "Image '$imagestream' part of the incompatible images. Skipping it."
        return
    fi

    if ! ./run_toolbox.py notebooks benchmark_performance \
         --imagestream "$imagestream" \
         $imagestream_tag \
         --namespace "$namespace" \
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
    cp  "$TOPSAIL_FROM_CONFIG_FILE" "$last_test_dir/config.yaml" || true

    if test_config clusters.sutest.is_metal; then
        cat <<EOF > "$last_test_dir/settings.instance_type" || true
instance_type=$(get_config clusters.create.ocp.compute.type)
EOF
    else
        cat <<EOF > "$last_test_dir/settings.instance_type" || true
instance_type=$instance_type
EOF
    fi
}

run_single_notebook_tests_run_benchmarks() {
    local notebook_performance_test="$1"
    local instance_type="$2"

    local imagestream=$(echo "$notebook_performance_test" | jq -r .imagestream)

    for benchmark in $(echo "$notebook_performance_test" | jq .benchmarks[] --compact-output); do
        if [[ "$imagestream" != "all" ]]; then
            run_single_notebook_tests_run_benchmark_against_imagestream "$notebook_performance_test" "$benchmark" "$instance_type" "$imagestream"
            continue
        fi

        local all_istags=$(oc get istag -n redhat-ods-applications -oname | cut -d/ -f2)
        echo "$all_istags" > "$ARTIFACT_DIR/istags.list"
        oc get istag -n redhat-ods-applications > "$ARTIFACT_DIR/istags.status"
        for istag in $all_istags; do
            local istream=$(echo "$istag" | cut -d: -f1)
            local istag=$(echo "$istag" | cut -d: -f2)

            run_single_notebook_tests_run_benchmark_against_imagestream "$notebook_performance_test" "$benchmark" "$instance_type"  "$istream" "$istag"

            if test_config tests.notebook_performance.test_only_one_image; then
                _info "tests.notebook_performance.test_only_one_image is set, stopping the imagetag loop after the first test."
                break
            fi
        done
    done
}

single_notebook_tests_prepare_instance_type() {
    local instance_type="$1"

    if ! test_config clusters.sutest.is_metal; then
        local machineset_name=$(get_command_arg name cluster set_scale --suffix notebook-performance)
        local machineset_instance_type=$(oc get machineset rhods-compute-pods -n openshift-machine-api -ojsonpath={.spec.template.spec.providerSpec.value.instanceType} --ignore-not-found)
        if [[ "$machineset_instance_type" != "$instance_type" ]]; then
            oc delete "machineset/$machineset_name" \
               -n openshift-machine-api \
               --ignore-not-found
        fi

        ./run_toolbox.py from_config cluster set_scale \
                         --suffix notebook-performance \
                         --extra "{instance_type:'$instance_type'}"
    fi
}

run_single_notebook_tests() {
    switch_sutest_cluster # should have only one cluster for this test

    local failed=0

    local namespace=$(get_command_arg namespace notebooks benchmark_performance)
    local toleration_key=$(get_config clusters.driver.compute.machineset.taint.key)

    local notebook_performance_tests=$(get_config tests.notebooks.notebook_performance.tests[])
    for notebook_performance_test in $(echo "$notebook_performance_tests" | jq --compact-output); do
        local instance_types=$(echo "$notebook_performance_test" | jq -r .instance_types[])

        for instance_type in $instance_types; do
            single_notebook_tests_prepare_instance_type "$instance_type"
            run_single_notebook_tests_run_benchmarks "$notebook_performance_test" "$instance_type"

            if test_config clusters.sutest.is_metal; then
                break
            fi
        done
    done

    set_config matbench.test_directory "$ARTIFACT_DIR"

    return $failed
}
