#! /bin/bash -e

THIS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

cat <<EOF
###
# Running diagnose scripts to validate the different
# steps of the GPU Operator deployment
###

EOF

source ${THIS_DIR}/../_common.sh

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

    cat <<EOF

Problem detected with '$@', capturing extra information...
EOF

    toolbox/capture_environment.sh > /dev/null || true
    toolbox/gpu-operator/capture_deployment_state.sh > /dev/null || true

    cat <<EOF

### FAILURE ###
# $@ --> failed
# $failure_msg
# The test artifacts have been stored in ${ARTIFACT_DIR}
###############
EOF

    return 1
}

do_test "The cluster is reachable" \
        "The cluster is not reachable. Are 'oc' and 'KUBECONFIG' properly configured?" \
        oc version

do_test "The cluster has the NFD operator" \
        "There is no NFD-labelled node. Is the NFD operator running properly?" \
        toolbox/nfd/has_nfd_labels.sh

do_test "The cluster is entitled" \
        "The cluster isn't entitled" \
        toolbox/entitlement/test.sh

do_test "The cluster has NFD and GPU nodes" \
        "There is no NFD-labelled GPU node. Is there a GPU node in the cluster?" \
        toolbox/nfd/has_gpu_nodes.sh

do_test "The GPU Operator is properly deployed" \
        "The GPU Operator isn't properly deployed." \
        toolbox/gpu-operator/wait_deployment.sh

do_test "The cluster is able to run GPU workload" \
        "The cluster is unable to run GPU workload" \
        toolbox/gpu-operator/run_gpu_burn.sh 30

do_test "All the relevant output logs have been captured in ${ARTIFACT_DIR}" \
        "(this step shouldn't fail)" \
        toolbox/gpu-operator/capture_deployment_state.sh

cat <<EOF
######################################
# The GPU Operator is up and running #
######################################
EOF
