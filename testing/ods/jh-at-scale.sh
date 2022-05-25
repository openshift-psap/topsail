#! /bin/bash

set -o errexit
set -o pipefail
set -o nounset
set -x

THIS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

source "$THIS_DIR/../prow/_logging.sh"

source "$THIS_DIR/common.sh"

# simulate two clusters

KUBECONFIG_DRIVER="$KUBECONFIG" # cluster driving the test
KUBECONFIG_SUTEST="/tmp/kubeconfig_sutest" # system under test

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

oc_adm_groups_new_rhods_users() {
    group=$1
    shift
    user_prefix=$1
    shift
    nb_users=$1

    oc delete groups.user.openshift.io/rhods-users --ignore-not-found

    echo "Adding $nb_users user with prefix '$user_prefix' in the group '$group' ..."
    users=$(for i in $(seq 0 $nb_users); do echo ${user_prefix}$i; done)
    oc adm groups new $group $(echo $users)
}

# ---
i=0
wait_list=()

run_in_bg() {
    "$@" &
    echo "Adding '$!' to the wait-list '${wait_list[@]}' ..."
    wait_list+=("$!")
}

wait_bg_processes() {
    echo "Waiting for the background processes '${wait_list[@]}' to terminate ..."
    for pid in ${wait_list[@]}; do
        wait $pid # this syntax honors the `set -e` flag
    done
    echo "All the processes are done!"
}

kill_bg_processes() {
    echo "Killing the background processes '${wait_list[@]}' still running ..."
    for pid in ${wait_list[@]}; do
        kill -9 $pid || true
    done
    echo "All the processes have been terminated."
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

    run_in_bg ./run_toolbox.py utils build_push_image \
                     "${ODS_CI_IMAGESTREAM}" "$ODS_CI_TAG" \
                     --namespace="$ODS_CI_TEST_NAMESPACE" \
                     --git-repo="$ODS_CI_REPO" \
                     --git-ref="$ODS_CI_REF" \
                     --context-dir="/" \
                     --dockerfile-path="build/Dockerfile"

    run_in_bg ./run_toolbox.py cluster deploy_minio_s3_server "$S3_LDAP_PROPS"
}

prepare_sutest_cluster() {
    osd_cluster_name=$1

    if [[ "$osd_cluster_name" ]]; then
        prepare_osd_sutest_cluster "$osd_cluster_name"
    else
       prepare_ocp_sutest_cluster
    fi
}

prepare_osd_sutest_cluster() {
    osd_cluster_name=$1

    switch_sutest_cluster

    run_in_bg ./run_toolbox.py rhods deploy_addon "$osd_cluster_name"

    run_in_bg ./run_toolbox.py rhods deploy_ldap \
              "$LDAP_IDP_NAME" "$ODS_CI_USER_PREFIX" "$ODS_CI_NB_USERS" "$S3_LDAP_PROPS" \
              --use_ocm="$osd_cluster_name" \
              --wait
}

prepare_ocp_sutest_cluster() {
    switch_sutest_cluster

    ./run_toolbox.py cluster set-scale m5.xlarge 5 --force

    run_in_bg ./run_toolbox.py rhods deploy_ldap "$LDAP_IDP_NAME" "$ODS_CI_USER_PREFIX" "$ODS_CI_NB_USERS" "$S3_LDAP_PROPS"

    echo "Deploying ODS $ODS_CATALOG_IMAGE_VERSION (from $ODS_CATALOG_VERSION)"

    run_in_bg ./run_toolbox.py rhods deploy_ods "$ODS_CATALOG_VERSION" "$ODS_CATALOG_IMAGE_VERSION"

    oc_adm_groups_new_rhods_users "$ODS_CI_USER_GROUP" "$ODS_CI_USER_PREFIX" "$ODS_CI_NB_USERS"
}

reset_prometheus() {
    switch_driver_cluster
    ./run_toolbox.py cluster reset_prometheus_db

    switch_sutest_cluster
    ./run_toolbox.py cluster reset_prometheus_db
    ./run_toolbox.py rhods reset_prometheus_db
}

collect_sutest() {
    switch_sutest_cluster
    ./run_toolbox.py rhods capture_state > /dev/null || true
    ./run_toolbox.py cluster capture_environment > /dev/null || true
}

delete_rhods_postgres() {
    switch_sutest_cluster

    # Destroy Postgres database to avoid AWS leaks ...
    # See https://issues.redhat.com/browse/MGDAPI-4118

    if ! oc delete postgres/jupyterhub-db-rds -n redhat-ods-applications --ignore-not-found; then
        echo "WARNING: Postgres database could not be deleted ..."
    fi
}

finalizers+=("kill_bg_processes")
finalizers+=("collect_sutest")
finalizers+=("delete_rhods_postgres")


OSD_CLUSTER_NAME=$(get_osd_cluster_name)
connect_sutest_cluster "$OSD_CLUSTER_NAME"

prepare_sutest_cluster "$OSD_CLUSTER_NAME"
prepare_driver_cluster

wait_bg_processes

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

switch_sutest_cluster
./run_toolbox.py cluster dump_prometheus_db
./run_toolbox.py rhods dump_prometheus_db
