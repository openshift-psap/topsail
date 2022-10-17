#! /bin/bash

set -o errexit
set -o pipefail
set -o nounset
set -o errtrace
set -x

source "$TESTING_ODS_DIR/../_logging.sh"
source "$TESTING_ODS_DIR/configure.sh"

#
# Configuration the test and the environment
#

BASE_ARTIFACT_DIR=${ARTIFACT_DIR:-/tmp/rhods_scale_test}
mkdir -p "$BASE_ARTIFACT_DIR"

if [[ "${INSIDE_CI_IMAGE:-}" == "y" ]]; then
    if [[ "${CONFIG_DEST_DIR:-}" ]]; then
        echo "Using CONFIG_DEST_DIR=$CONFIG_DEST_DIR ..."

    elif [[ "${SHARED_DIR:-}" ]]; then
        echo "Using CONFIG_DEST_DIR=\$SHARED_DIR=$SHARED_DIR ..."
        CONFIG_DEST_DIR=$SHARED_DIR

    else
        _error "CONFIG_DEST_DIR or SHARED_DIR must be set ..."
    fi

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

action=${1:-}
case ${action} in
    "prepare")
        # 1. Configure the clusters

        # 1.0 Deploy RHODS in the sutest cluster

        testing/ods/notebook_scale_test.sh deploy_rhods
        testing/ods/notebook_scale_test.sh wait_rhods

        # 1.1 Deploy LDAP in the sutest cluster

        testing/ods/notebook_scale_test.sh deploy_ldap

        # 1.2 Prepare the driver cluster

        testing/ods/notebook_scale_test.sh prepare_driver_cluster

        # 1.3 Prepare the laptop for generating the plots

        testing/ods/notebook_scale_test.sh prepare_matbench
        exit 0
        ;;
    "test")
        #
        # 2. Run the tests in a dedicated ARTIFACT_DIR directory
        #

        # 2.1 Run the first test

        export ARTIFACT_DIR="${BASE_ARTIFACT_DIR}/test_1"

        set_config tests.notebooks.users.count 4
        set_config tests.notebooks.users.sleep_factor 2 # seconds

        testing/ods/notebook_scale_test.sh run_test_and_plot

        # 2.2 Run the second test

        export ARTIFACT_DIR="${BASE_ARTIFACT_DIR}/test_2"
        set_config tests.notebooks.users.count 3
        set_config tests.notebooks.users.sleep_factor 1 # seconds

        testing/ods/notebook_scale_test.sh run_test
        testing/ods/notebook_scale_test.sh generate_plots

        #
        # 3. Cleanup the RHODS cluster
        #

        export ARTIFACT_DIR="${BASE_ARTIFACT_DIR}/preparation"

        # 3.1 Undeploy LDAP in the sutest cluster

        testing/ods/notebook_scale_test.sh undeploy_ldap
        ;;
    *)
        _error "$0: unknown action '$action'"
        exit 1
        ;;
esac
