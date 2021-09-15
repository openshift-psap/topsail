#! /bin/bash -e

THIS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd ${THIS_DIR}/../..

RUN_ALL="$([[ "$*" == *"--run-all"* ]] && echo "yes" || echo "no")"
has_errors=0

cat <<EOF
###
# Running diagnose scripts to validate the different
# steps of the GPU Operator deployment
###

EOF


do_test() {
    success_msg="$1"
    failure_msg="$2"

    shift;shift
    # script: "$@"

    cat <<EOF

# $(basename "$0"): Running $@

EOF

    if "$@"; then
        cat <<EOF

###
# $@ --> success
# $success_msg
###

EOF
        return 0
    fi

    if [[ $RUN_ALL != yes ]]; then
        cat <<EOF

Problem detected with '$@', capturing extra information...
EOF
        ./run_toolbox.py gpu_operator capture_deployment_state > /dev/null || true
        ./run_toolbox.py gpu_operator get_csv_version > /dev/null || true
    fi

    cat <<EOF

### FAILURE ###
# $@ --> failed
# $failure_msg
# The test artifacts have been stored in ${ARTIFACT_DIR}
###############
EOF

    if [[ $RUN_ALL == yes ]]; then
        has_errors=$(($has_errors + 1))
        return 0
    else
        return 1
    fi
}

if [[ $RUN_ALL == yes ]]; then
    echo "Capture the operator version ..."
    ./run_toolbox.py gpu_operator get_csv_version > /dev/null || true
    echo "Capture the deployment state ..."
    ./run_toolbox.py gpu_operator capture_deployment_state > /dev/null || true
    echo "Capture the cluster environment ..."
    ./run_toolbox.py cluster capture_environment > /dev/null || true
    echo "Done with the state capture."
fi

do_test "The cluster is reachable" \
        "The cluster is not reachable. Are 'oc' and 'KUBECONFIG' properly configured?" \
        oc version

do_test "The cluster has the NFD operator" \
        "There is no NFD-labelled node. Is the NFD operator running properly?" \
        ./run_toolbox.py nfd has_labels

do_test "The cluster is entitled" \
        "The cluster isn't entitled" \
        ./run_toolbox.py entitlement test_cluster

do_test "The cluster has NFD and GPU nodes" \
        "There is no NFD-labelled GPU node. Is there a GPU node in the cluster?" \
        ./run_toolbox.py nfd has_gpu_nodes

if [[ "$has_errors" == 0 ]]; then
    do_test "The GPU Operator is properly deployed" \
            "The GPU Operator isn't properly deployed." \
            ./run_toolbox.py gpu_operator wait_deployment
else
    echo "Found errors with the GPU Operator, skipping the deployment testing."
fi

if [[ "$has_errors" == 0 ]]; then
    do_test "The cluster is able to run GPU workload" \
            "The cluster is unable to run GPU workload" \
            ./run_toolbox.py gpu_operator run_gpu_burn --runtime=30
else
    echo "Found errors with the GPU Operator, skipping GPU-Burn testing."
fi

./run_toolbox.py cluster capture_environment > /dev/null || true

if [[ "$has_errors" == 0 ]]; then
    cat <<EOF
######################################
# The GPU Operator is up and running #
######################################
EOF
else
    cat <<EOF
###############################################
# Found multiple errors with the GPU Operator #
###############################################
EOF
fi
