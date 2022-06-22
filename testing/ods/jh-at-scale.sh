#! /bin/bash

set -o errexit
set -o pipefail
set -o nounset
set -x

THIS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

source "$THIS_DIR/../prow/_logging.sh"
source "$THIS_DIR/process_ctrl.sh"
source "$THIS_DIR/common.sh"

KUBECONFIG_DRIVER="${KUBECONFIG_DRIVER:-${SHARED_DIR}/driver_kubeconfig}" # cluster driving the test
KUBECONFIG_SUTEST="${KUBECONFIG_SUTEST:-${SHARED_DIR}/sutest_kubeconfig}" # system under test

DRIVER_CLUSTER=driver
SUTEST_CLUSTER=sutest

switch_sutest_cluster() {
    switch_cluster "$SUTEST_CLUSTER"
}

switch_driver_cluster() {
    switch_cluster "$DRIVER_CLUSTER"
}

switch_cluster() {
    cluster="$1"
    echo "Switching to the '$cluster' cluster"
    if [[ "$cluster" == "$DRIVER_CLUSTER" ]]; then
        export KUBECONFIG=$KUBECONFIG_DRIVER
    elif [[ "$cluster" == "$SUTEST_CLUSTER" ]]; then
        export KUBECONFIG=$KUBECONFIG_SUTEST
    else
        echo "Requested to switch to an unknown cluster '$cluster', exiting."
        exit 1
    fi
}

# ---

connect_sutest_cluster() {
    osd_cluster_name=$1

    touch "$KUBECONFIG_SUTEST"

    switch_sutest_cluster

    if [[ "$osd_cluster_name" ]]; then
        echo "OSD cluster name is $osd_cluster_name"

        ocm_login

        if ! ocm_cluster_is_ready "$osd_cluster_name"
        then
            echo "OCM cluster '$osd_cluster_name' isn't ready ..."
            exit 1
        fi

        ocm_oc_login "$osd_cluster_name"
    fi

    oc get clusterversion
}

prepare_driver_cluster() {
    switch_cluster "driver"

    oc create namespace "$ODS_CI_TEST_NAMESPACE" -oyaml --dry-run=client | oc apply -f-

    process_ctrl::run_in_bg ./run_toolbox.py utils build_push_image \
                     "${ODS_CI_IMAGESTREAM}" "$ODS_CI_TAG" \
                     --namespace="$ODS_CI_TEST_NAMESPACE" \
                     --git-repo="$ODS_CI_REPO" \
                     --git-ref="$ODS_CI_REF" \
                     --context-dir="/" \
                     --dockerfile-path="build/Dockerfile"

    process_ctrl::run_in_bg ./run_toolbox.py cluster deploy_minio_s3_server "$S3_LDAP_PROPS"
}

prepare_sutest_cluster() {
    osd_cluster_name=$1

    switch_sutest_cluster

    if [[ "$osd_cluster_name" ]]; then
        prepare_osd_sutest_cluster "$osd_cluster_name"
    else
        if [[ "${INSIDE_CI_IMAGE:-}" ]]; then
            echo "FATAL: Deployment on OCP currently disabled (hardcoded). "
            echo "Remove this we it is safe to deploy on OCP with guarantee not to leak any AWS resources."
            exit 1
        fi

        prepare_ocp_sutest_cluster
    fi

    process_ctrl::run_in_bg ./run_toolbox.py rhods deploy_ldap \
              "$LDAP_IDP_NAME" "$ODS_CI_USER_PREFIX" "$ODS_CI_NB_USERS" "$S3_LDAP_PROPS" \
              --use_ocm="$osd_cluster_name" \
              --wait
}

prepare_osd_sutest_cluster() {
    osd_cluster_name=$1

    if [[ "$OSD_USE_ODS_CATALOG" == 1 ]]; then
        echo "Deploying RHODS $ODS_QE_CATALOG_IMAGE_TAG (from $ODS_QE_CATALOG_IMAGE)"

        process_ctrl::run_in_bg ./run_toolbox.py rhods deploy_ods \
                  "$ODS_QE_CATALOG_IMAGE" "$ODS_QE_CATALOG_IMAGE_TAG"
    else

        if [[ "$OCM_ENV" == "staging" ]]; then
            echo "Workaround for https://issues.redhat.com/browse/RHODS-4182"
            MISSING_SECRET_NAMESPACE=redhat-ods-monitoring

            oc create ns "$MISSING_SECRET_NAMESPACE" \
               --dry-run=client \
               -oyaml \
                | oc apply -f-

            oc create secret generic redhat-rhods-smtp \
               -n "$MISSING_SECRET_NAMESPACE" \
               --from-literal=host= \
               --from-literal=username= \
               --from-literal=password= \
               --from-literal=port= \
               --from-literal=tls=
        fi

        process_ctrl::run_in_bg ./run_toolbox.py rhods deploy_addon "$osd_cluster_name"
    fi
}

prepare_ocp_sutest_cluster() {
    switch_sutest_cluster

    ./run_toolbox.py cluster set-scale m5.xlarge 5 --force

    process_ctrl::run_in_bg ./run_toolbox.py rhods deploy_ldap \
                            "$LDAP_IDP_NAME" "$ODS_CI_USER_PREFIX" "$ODS_CI_NB_USERS" "$S3_LDAP_PROPS"

    echo "Deploying RHODS $ODS_QE_CATALOG_IMAGE_TAG (from $ODS_QE_CATALOG_IMAGE)"

    process_ctrl::run_in_bg ./run_toolbox.py rhods deploy_ods \
                            "$ODS_QE_CATALOG_IMAGE" "$ODS_QE_CATALOG_IMAGE_TAG"
}

wait_rhods_launch() {
    switch_sutest_cluster

    ./run_toolbox.py rhods wait_ods
}

reset_prometheus() {
    switch_driver_cluster
    ./run_toolbox.py cluster reset_prometheus_db

    switch_sutest_cluster
    ./run_toolbox.py cluster reset_prometheus_db
    ./run_toolbox.py rhods reset_prometheus_db
}

capture_environment() {
    switch_sutest_cluster
    ./run_toolbox.py rhods capture_state > /dev/null || true
    ./run_toolbox.py cluster capture_environment > /dev/null || true

    switch_driver_cluster
    ./run_toolbox.py cluster capture_environment > /dev/null || true
}

dump_prometheus_dbs() {
    switch_sutest_cluster
    process_ctrl::run_in_bg ./run_toolbox.py cluster dump_prometheus_db
    process_ctrl::run_in_bg ./run_toolbox.py rhods dump_prometheus_db

    switch_driver_cluster
    process_ctrl::run_in_bg ./run_toolbox.py cluster dump_prometheus_db

    process_ctrl::wait_bg_processes
}

run_multi_cluster() {
    finalizers+=("process_ctrl::kill_bg_processes")
    finalizers+=("capture_environment")

    sutest_osd_cluster_name=$(get_osd_cluster_name "sutest")
    connect_sutest_cluster "$sutest_osd_cluster_name"
    prepare_sutest_cluster "$sutest_osd_cluster_name"

    prepare_driver_cluster

    process_ctrl::wait_bg_processes

    wait_rhods_launch

    reset_prometheus

    switch_driver_cluster

    if [[ "$ODS_CI_NB_USERS" -le 5 ]]; then
        collect=all
    else
        collect=no-image
    fi

    ./run_toolbox.py rhods test_jupyterlab \
                     "$LDAP_IDP_NAME" \
                     "$ODS_CI_USER_PREFIX" "$ODS_CI_NB_USERS" \
                     "$S3_LDAP_PROPS" \
                     --sut_cluster_kubeconfig="$KUBECONFIG_SUTEST" \
                     --artifacts-collected=$collect


    dump_prometheus_dbs
}

run_prepare_local_cluster() {
    prepare_driver_cluster
    prepare_sutest_cluster "$(get_osd_cluster_name "sutest")"

    process_ctrl::wait_bg_processes

    wait_rhods_launch
}

# ---

switch_driver_cluster
oc get clusterversion/version
oc whoami --show-console

switch_sutest_cluster
oc get clusterversion/version
oc whoami --show-console

action=${1:-run_multi_cluster}

case ${action} in
    "run_multi_cluster")
        run_multi_cluster "$@"
        exit 0
        ;;
    "run_prepare_local_cluster")
        run_prepare_local_cluster "$@"
        exit 0
        ;;
    "source")
        # file is being sourced by another script
        ;;
    *)
        echo "FATAL: Unknown action: ${action}" "$@"
        exit 1
        ;;
esac
