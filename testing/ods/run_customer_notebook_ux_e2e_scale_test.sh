#! /bin/bash

set -o errexit
set -o pipefail
set -o nounset
set -o errtrace
set -x

#
# Configuration the test and the environment
#

# export OSD_CLUSTER_NAME=<osd cluster name> # OCM name of the cluster, empty if OCP
# export ODS_CI_NB_USERS=10 # number of users to simulate
# export ODS_SLEEP_FACTOR=1 # how long to wait between user starts, in seconds

BASE_ARTIFACT_DIR=${ARTIFACT_DIR:-/tmp/rhods_scale_test}
mkdir -p "$BASE_ARTIFACT_DIR"

if [[ "${INSIDE_CI_IMAGE:-}" == "y" ]]; then
    KUBECONFIG_DRIVER="${SHARED_DIR}/driver_kubeconfig" # cluster driving the test
    KUBECONFIG_SUTEST="${SHARED_DIR}/sutest_kubeconfig" # system under test
else
    KUBECONFIG_DRIVER="${KUBECONFIG_DRIVER:-$KUBECONFIG}" # cluster driving the test
    KUBECONFIG_SUTEST="${KUBECONFIG_SUTEST:-$KUBECONFIG}" # system under test
fi

# These environment variables are used in the scripts to refer to the
# driver/sutest clusters
export KUBECONFIG_DRIVER
export KUBECONFIG_SUTEST

export ARTIFACT_DIR="${BASE_ARTIFACT_DIR}/preparation"

# 1. Configure the clusters

# 1.0 Deploy RHODS in the sutest cluster

testing/ods/notebook_ux_e2e_scale_test.sh deploy_rhods
testing/ods/notebook_ux_e2e_scale_test.sh wait_rhods

# 1.1 Deploy LDAP in the sutest cluster

testing/ods/notebook_ux_e2e_scale_test.sh deploy_ldap

# 1.2 Prepare the driver cluster

testing/ods/notebook_ux_e2e_scale_test.sh prepare_driver_cluster

# 1.3 Prepare the laptop for generating the plots

testing/ods/generate_matrix-benchmarking.sh prepare_matbench

#
# 2. Run the tests in a dedicated ARTIFACT_DIR directory
#

# 2.1 Run the first test

export ARTIFACT_DIR="${BASE_ARTIFACT_DIR}/test_1"
export ODS_CI_NB_USERS=4
export ODS_SLEEP_FACTOR=2

testing/ods/notebook_ux_e2e_scale_test.sh run_test_and_plot

# 2.2 Run the second test

export ARTIFACT_DIR="${BASE_ARTIFACT_DIR}/test_2"
export ODS_CI_NB_USERS=3
export ODS_SLEEP_FACTOR=1

testing/ods/notebook_ux_e2e_scale_test.sh run_test_and_plot

#
# 3. Cleanup the RHODS cluster
#

export ARTIFACT_DIR="${BASE_ARTIFACT_DIR}/preparation"

# 3.1 Undeploy LDAP in the sutest cluster

testing/ods/notebook_ux_e2e_scale_test.sh undeploy_ldap
