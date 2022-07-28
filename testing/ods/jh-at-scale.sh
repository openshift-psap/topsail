#! /bin/bash

set -o errexit
set -o pipefail
set -o nounset
set -o errtrace
set -x

THIS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

source "$THIS_DIR/../prow/_logging.sh"
source "$THIS_DIR/process_ctrl.sh"
source "$THIS_DIR/common.sh"

if [[ "${INSIDE_CI_IMAGE:-}" == "y" ]]; then
    KUBECONFIG_DRIVER="${SHARED_DIR}/driver_kubeconfig" # cluster driving the test
    KUBECONFIG_SUTEST="${SHARED_DIR}/sutest_kubeconfig" # system under test
else
    KUBECONFIG_DRIVER="${KUBECONFIG_DRIVER:-$KUBECONFIG}" # cluster driving the test
    KUBECONFIG_SUTEST="${KUBECONFIG_SUTEST:-$KUBECONFIG}" # system under test
fi

DRIVER_CLUSTER=driver
SUTEST_CLUSTER=sutest

switch_sutest_cluster() {
    switch_cluster "$SUTEST_CLUSTER"
}

switch_driver_cluster() {
    switch_cluster "$DRIVER_CLUSTER"
}

switch_cluster() {
    cluster_role="$1"
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

    build_and_preload_odsci_image() {
        ./run_toolbox.py utils build_push_image \
                         "$ODS_CI_IMAGESTREAM" "$ODS_CI_TAG" \
                         --namespace="$ODS_CI_TEST_NAMESPACE" \
                         --git-repo="$ODS_CI_REPO" \
                         --git-ref="$ODS_CI_REF" \
                         --context-dir="/" \
                         --dockerfile-path="build/Dockerfile"

        ods_ci_image="image-registry.openshift-image-registry.svc:5000/$ODS_CI_TEST_NAMESPACE/$ODS_CI_IMAGESTREAM:$ODS_CI_TAG"
        ./run_toolbox.py cluster preload_image "ods-ci-image" "$ods_ci_image" \
                         --namespace="$ODS_CI_TEST_NAMESPACE"
    }

    build_and_preload_artifacts_exporter_image() {
        ./run_toolbox.py utils build_push_image \
                         "$ODS_CI_IMAGESTREAM" "$ODS_CI_ARTIFACTS_EXPORTER_TAG" \
                         --namespace="$ODS_CI_TEST_NAMESPACE" \
                         --context-dir="/" \
                         --dockerfile-path="$ODS_CI_ARTIFACTS_EXPORTER_DOCKERFILE"

        artifacts_exporter_image="image-registry.openshift-image-registry.svc:5000/$ODS_CI_TEST_NAMESPACE/$ODS_CI_IMAGESTREAM:$ODS_CI_ARTIFACTS_EXPORTER_TAG"
        ./run_toolbox.py cluster preload_image "ods-ci-artifacts-exporter-image" "$artifacts_exporter_image" \
                         --namespace="$ODS_CI_TEST_NAMESPACE"
    }

    process_ctrl::run_in_bg build_and_preload_odsci_image
    process_ctrl::run_in_bg build_and_preload_artifacts_exporter_image

    process_ctrl::run_in_bg ./run_toolbox.py cluster deploy_minio_s3_server "$S3_LDAP_PROPS"

    process_ctrl::run_in_bg ./run_toolbox.py cluster deploy_nginx_server "$NGINX_NOTEBOOK_NAMESPACE" "$ODS_NOTEBOOK_DIR"
}

prepare_sutest_install_rhods() {
    switch_sutest_cluster

    osd_cluster_name=$(get_osd_cluster_name "sutest")

    if [[ "$osd_cluster_name" ]]; then
        prepare_osd_sutest_install_rhods "$osd_cluster_name"
    else
        prepare_ocp_sutest_install_rhods
    fi
}

prepare_sutest_install_ldap() {
    switch_sutest_cluster

    osd_cluster_name=$(get_osd_cluster_name "sutest")

    process_ctrl::run_in_bg ./run_toolbox.py cluster deploy_ldap \
              "$LDAP_IDP_NAME" "$ODS_CI_USER_PREFIX" "$ODS_CI_NB_USERS" "$S3_LDAP_PROPS" \
              --use_ocm="$osd_cluster_name" \
              --wait
}

prepare_sutest_cluster() {
    switch_sutest_cluster
    prepare_sutest_install_rhods
    prepare_sutest_install_ldap
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

        process_ctrl::run_in_bg ./run_toolbox.py rhods deploy_addon "$osd_cluster_name" "$ODS_ADDON_EMAIL_ADDRESS"
    fi
}

prepare_ocp_sutest_cluster() {
    switch_sutest_cluster

    echo "Deploying RHODS $ODS_QE_CATALOG_IMAGE_TAG (from $ODS_QE_CATALOG_IMAGE)"

    process_ctrl::run_in_bg \
        process_ctrl::retry 5 3m \
            ./run_toolbox.py rhods deploy_ods \
                "$ODS_QE_CATALOG_IMAGE" "$ODS_QE_CATALOG_IMAGE_TAG"
}

wait_rhods_launch() {
    switch_sutest_cluster

    ./run_toolbox.py rhods wait_ods

    if [[ -z "$ENABLE_AUTOSCALER" ]]; then
        rhods_notebook_image_tag=$(oc get istag -n redhat-ods-applications -oname \
                                       | cut -d/ -f2 | grep "$RHODS_NOTEBOOK_IMAGE_NAME" | cut -d: -f2)

        NOTEBOOK_IMAGE="image-registry.openshift-image-registry.svc:5000/redhat-ods-applications/$RHODS_NOTEBOOK_IMAGE_NAME:$rhods_notebook_image_tag"
        # preload the image only if auto-scaling is disabled
        ./run_toolbox.py cluster preload_image "$RHODS_NOTEBOOK_IMAGE_NAME" "$NOTEBOOK_IMAGE" \
                         --namespace=rhods-notebooks
    fi
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

prepare_ci() {
    cp "$THIS_DIR/common.sh" "$ARTIFACT_DIR" # save the settings of this run

    sutest_osd_cluster_name=$(get_osd_cluster_name "sutest")
    connect_sutest_cluster "$sutest_osd_cluster_name"
}

prepare() {
    prepare_sutest_cluster
    prepare_driver_cluster

    process_ctrl::wait_bg_processes

    wait_rhods_launch
}

run_jupyterlab_test() {
    switch_driver_cluster

    NGINX_SERVER="nginx-$NGINX_NOTEBOOK_NAMESPACE"
    nginx_hostname=$(oc whoami --show-server | sed "s/api/$NGINX_SERVER.apps/g" | awk -F ":" '{print $2}' | sed s,//,,g)

    ./run_toolbox.py rhods test_jupyterlab \
                     "$LDAP_IDP_NAME" \
                     "$ODS_CI_USER_PREFIX" "$ODS_CI_NB_USERS" \
                     "$S3_LDAP_PROPS" \
                     "http://$nginx_hostname/$ODS_NOTEBOOK_NAME" \
                     --sut_cluster_kubeconfig="$KUBECONFIG_SUTEST" \
                     --artifacts-collected="$ODS_CI_ARTIFACTS_COLLECTED" \
                     --ods_sleep_factor="$ODS_SLEEP_FACTOR" \
                     --ods_ci_exclude_tags="$ODS_EXCLUDE_TAGS" \
                     --ods_ci_artifacts_exporter_istag="$ODS_CI_IMAGESTREAM:$ODS_CI_ARTIFACTS_EXPORTER_TAG" \
                     --ods_ci_notebook_image_name="$RHODS_NOTEBOOK_IMAGE_NAME"

    # quick access to these files
    cp "$ARTIFACT_DIR"/*__driver_rhods__test_jupyterlab/{failed_tests,success_count} "$ARTIFACT_DIR" || true
}

sutest_cleanup() {
    switch_sutest_cluster
    sutest_cleanup_ldap
}

sutest_cleanup_ldap() {
    switch_sutest_cluster

    osd_cluster_name=$(get_osd_cluster_name "sutest")

    if oc get cm/keep-cluster -n default 2>/dev/null; then
        echo "INFO: cm/keep-cluster found, not undeploying LDAP."
    else
        ./run_toolbox.py cluster undeploy_ldap \
                         "$LDAP_IDP_NAME" \
                         --use_ocm="$osd_cluster_name" > /dev/null
    fi
}

run_prepare_local_cluster() {
    prepare_driver_cluster
    prepare_sutest_cluster "$(get_osd_cluster_name "sutest")"

    process_ctrl::wait_bg_processes

    wait_rhods_launch
}

generate_plots() {
    mkdir "$ARTIFACT_DIR/plotting"
    ARTIFACT_DIR="$ARTIFACT_DIR/plotting" ./testing/ods/generate_matrix-benchmarking.sh > "$ARTIFACT_DIR/plotting/build-log.txt" 2>&1
}

# ---

finalizers+=("process_ctrl::kill_bg_processes")

switch_driver_cluster
oc get clusterversion/version
oc whoami --show-console

switch_sutest_cluster
oc get clusterversion/version
oc whoami --show-console

action=${1:-run_ci_e2e_test}

case ${action} in
    "run_ci_e2e_test")
        if [ -z "${SHARED_DIR:-}" ]; then
            echo "FATAL: multi-stage test \$SHARED_DIR not set ..."
            exit 1
        fi
        finalizers+=("capture_environment")
        finalizers+=("sutest_cleanup")
        # Generate the visualization reports (must run after dump_prometheus_dbs and capture_environment)
        finalizers+=("generate_plots")

        prepare_ci
        prepare
        run_jupyterlab_test

        set +e # we do not wait to fail passed this point
        dump_prometheus_dbs
        exit 0
        ;;
    "prepare")
        prepare
        exit 0
        ;;
    "install_rhods")
	prepare_sutest_install_rhods
	process_ctrl::wait_bg_processes
	exit 0
	;;
    "install_ldap")
	prepare_sutest_install_ldap
	process_ctrl::wait_bg_processes
	exit 0
	;;
    "uninstall_ldap")
	sutest_cleanup_ldap
	exit 0
	;;
    "prepare_driver_cluster")
	prepare_driver_cluster
	process_ctrl::wait_bg_processes
	exit 0
	;;
    "run_jupyterlab_test")
	run_jupyterlab_test
        dump_prometheus_dbs
        capture_environment
        exit 0
        ;;
    "generate_plots")
	export ARTIFACT_DIR="$ARTIFACT_DIR/plotting"
	mkdir -p "$ARTIFACT_DIR"
	exec ./testing/ods/generate_matrix-benchmarking.sh generate_plots
	;;
    "source")
        # file is being sourced by another script
        ;;
    *)
        echo "FATAL: Unknown action: ${action}" "$@"
        exit 1
        ;;
esac
