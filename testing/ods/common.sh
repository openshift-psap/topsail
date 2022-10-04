if [[ -z "${PSAP_ODS_SECRET_PATH:-}" ]]; then
    echo "ERROR: the PSAP_ODS_SECRET_PATH was not provided"
    false # can't exit here
elif [[ ! -d "$PSAP_ODS_SECRET_PATH" ]]; then
    echo "ERROR: the PSAP_ODS_SECRET_PATH does not point to a valid directory"
    false # can't exit here
fi

if [[ "${ARTIFACT_DIR:-}" ]] && [[ -f "${ARTIFACT_DIR}/variable_overrides" ]]; then
    # source before everything else, to allow if/then/else below based on PR-defined variables
    source "${ARTIFACT_DIR}/variable_overrides"
fi

OCM_ENV=staging # The valid aliases are 'production', 'staging', 'integration'

S3_LDAP_PROPS="${PSAP_ODS_SECRET_PATH}/s3_ldap.passwords"

# if 1, use the ODS_CATALOG_IMAGE OLM catalog.
# Otherwise, install RHODS from OCM addon.
OSD_USE_ODS_CATALOG=1

# If the value is set, consider SUTEST to be running on OSD or ROSA,
# and use this cluster name to configure LDAP and RHODS
# Note:
# * KEEP EMPTY IF SUTEST IS NOT ON OSD
# * KEEP EMPTY ON CI, OSD OR OCP ALIKE
OSD_CLUSTER_NAME=

# If the value is set, consider SUTEST to be running on ROSA
# * KEEP EMPTY ON CI
OSD_CLUSTER_IS_ROSA=

ODS_CATALOG_IMAGE="quay.io/modh/qe-catalog-source"
ODS_CATALOG_IMAGE_TAG="latest"

RHODS_NOTEBOOK_IMAGE_NAME=s2i-generic-data-science-notebook

ODS_CI_TEST_NAMESPACE=loadtest
ODS_CI_REPO="https://github.com/openshift-psap/ods-ci.git"
ODS_CI_REF="jh-at-scale.v220923"

ODS_CI_IMAGESTREAM="ods-ci"
ODS_CI_TAG="latest"
ODS_CI_ARTIFACTS_EXPORTER_TAG="artifacts-exporter"
ODS_CI_ARTIFACTS_EXPORTER_DOCKERFILE="testing/ods/images/Containerfile.s3_artifacts_exporter"

# if the value is different from 1, delete the test namespaces after the testing
CLEANUP_DRIVER_NAMESPACES_ON_EXIT=0

# if the value is different from 1, do not customize RHODS.
# see sutest_customize_rhods in `notebook_ux_e2e_scale_test.sh`.
CUSTOMIZE_RHODS=1

# only taken into account if CUSTOMIZE_RHODS=1
# if not empty, force the given image for the rhods-dashboard container
# Mind that this requires stopping the rhods-operator.
# ODH main image: quay.io/opendatahub/odh-dashboard:main
CUSTOMIZE_RHODS_DASHBOARD_FORCED_IMAGE=
CUSTOMIZE_RHODS_DASHBOARD_NAME=RHODS # must be ODH or RHODS, for ODS-CI to recognize the dashboard page

# only taken into account if CUSTOMIZE_RHODS=1
# if value is 1, remove the GPU images (to use less resources)
CUSTOMIZE_RHODS_REMOVE_GPU_IMAGES=1

# only taken into account if CUSTOMIZE_RHODS=1
# if value is not empty, use the given PVC size
CUSTOMIZE_RHODS_PVC_SIZE=5Gi

# only taken into account if CUSTOMIZE_RHODS=1
# if value is 1, define a custom notebook size named $ODS_NOTEBOOK_SIZE
# see sutest_customize_rhods_after_wait for the limits/requests values
CUSTOMIZE_RHODS_USE_CUSTOM_NOTEBOOK_SIZE=1

ODS_NOTEBOOK_CPU_SIZE=1
ODS_NOTEBOOK_MEMORY_SIZE_GI=4

# must be consistent with roles/rhods_notebook_ux_e2e_scale_test/templates/ods-ci_job.yaml
ODS_NOTEBOOK_SIZE=Tiny # needs to match an existing notebook size in OdhDashboardConfig.spec.notebookSizes
ODS_TESTPOD_CPU_SIZE=0.2
ODS_TESTPOD_MEMORY_SIZE_GI=0.75

# only taken into account if CUSTOMIZE_RHODS=1 and CUSTOMIZE_RHODS_DASHBOARD_FORCED_IMAGE is set
# number of replicas to set to the Dashboard deployment
CUSTOMIZE_RHODS_DASHBOARD_REPLICAS=5

LDAP_IDP_NAME=RHODS_CI_LDAP
LDAP_NB_USERS=1000

ODS_CI_NB_USERS=5 # number of users to simulate
ODS_CI_USER_PREFIX=psapuser

ODS_SLEEP_FACTOR=1.0 # how long to wait between user starts.
ODS_CI_ARTIFACTS_COLLECTED=no-image-except-failed-and-zero

STATESIGNAL_REDIS_NAMESPACE=loadtest-redis
NGINX_NOTEBOOK_NAMESPACE=loadtest-notebooks
ODS_NOTEBOOK_NAME=simple-notebook.ipynb

ODS_NOTEBOOK_BENCHMARK_NAME=pyperf_bm_go.py
ODS_NOTEBOOK_BENCHMARK_REPEAT=3
ODS_NOTEBOOK_BENCHMARK_NUMBER=20 # around 10s

ODS_NOTEBOOK_DIR=${THIS_DIR}/notebooks
ODS_EXCLUDE_TAGS=None # tags to exclude when running the robot test case

# number of test runs to perform
NOTEBOOK_TEST_RUNS=2

# if 1, the last test run will have only 1 user (for the notebook performance)
LAST_NOTEBOOK_TEST_RUN_IS_SINGLE=1

if [[ "$OSD_USE_ODS_CATALOG" == "0" ]]; then
    # deploying from the addon. Get the email address from the secret vault.
    ODS_ADDON_EMAIL_ADDRESS=$(cat "$PSAP_ODS_SECRET_PATH/addon.email")
fi

CLUSTER_NAME_PREFIX=odsci

OSD_VERSION=4.10.15
OSD_REGION=us-west-2

OSD_WORKER_NODES_TYPE=m6.xlarge
OSD_WORKER_NODES_COUNT=3

OCP_VERSION=4.10.15
OCP_REGION=us-west-2
OCP_MASTER_MACHINE_TYPE=m6a.xlarge
OCP_INFRA_MACHINE_TYPE=m6a.xlarge
OCP_INFRA_NODES_COUNT=2

OCP_BASE_DOMAIN=psap.aws.rhperfscale.org

# if not empty, enables auto-scaling in the sutest cluster
ENABLE_AUTOSCALER=

SUTEST_MACHINESET_NAME=rhods-notebooks
SUTEST_TAINT_KEY=only-$SUTEST_MACHINESET_NAME
SUTEST_TAINT_VALUE=yes
SUTEST_TAINT_EFFECT=NoSchedule
SUTEST_NODE_SELECTOR="$SUTEST_TAINT_KEY: '$SUTEST_TAINT_VALUE'"

DRIVER_MACHINESET_NAME=test-pods
DRIVER_TAINT_KEY=only-$DRIVER_MACHINESET_NAME
DRIVER_TAINT_VALUE=yes
DRIVER_TAINT_EFFECT=NoSchedule
DRIVER_NODE_SELECTOR="$DRIVER_TAINT_KEY: '$DRIVER_TAINT_VALUE'"

DRIVER_COMPUTE_MACHINE_TYPE=m5a.2xlarge
OSD_SUTEST_COMPUTE_MACHINE_TYPE=m5.2xlarge
OCP_SUTEST_COMPUTE_MACHINE_TYPE=m5a.2xlarge

SUTEST_FORCE_COMPUTE_NODES_COUNT= # if empty, uses ods/sizing/sizing to determine the right number of machines
DRIVER_FORCE_COMPUTE_NODES_COUNT= # if empty, uses ods/sizing/sizing to determine the right number of machines

# OSP/OSD cluster naming is handled differently in this job
JOB_NAME_SAFE_GET_CLUSTER="get-cluster"

# number of hours CI clusters are allowed to stay alive, before we clean them up
CLUSTER_CLEANUP_DELAY=4

if [[ "${ARTIFACT_DIR:-}" ]] && [[ -f "${ARTIFACT_DIR}/variable_overrides" ]]; then
    source "${ARTIFACT_DIR}/variable_overrides"
fi

if [[ "$ODS_CI_NB_USERS" -gt 120 ]]; then
    OCP_MASTER_MACHINE_TYPE=m5a.2xlarge
    OCP_INFRA_MACHINE_TYPE=r5a.xlarge
fi

# use FORCE_OCP_MASTER_MACHINE_TYPE and/or FORCE_OCP_INFRA_MACHINE_TYPE to override the machine type in variable_overrides
OCP_MASTER_MACHINE_TYPE=${FORCE_OCP_MASTER_MACHINE_TYPE:-$OCP_MASTER_MACHINE_TYPE}
OCP_INFRA_MACHINE_TYPE=${FORCE_OCP_INFRA_MACHINE_TYPE:-$OCP_INFRA_MACHINE_TYPE}

ocm_login() {
    export OCM_ENV
    export PSAP_ODS_SECRET_PATH

    # do it in a subshell to avoid leaking the `OCM_TOKEN` secret because of `set -x`
    bash -c '
      set -o errexit
      set -o nounset

      OCM_TOKEN=$(cat "$PSAP_ODS_SECRET_PATH/ocm.token" | grep "^${OCM_ENV}=" | cut -d= -f2-)
      echo "Login in $OCM_ENV with token length=$(echo "$OCM_TOKEN" | wc -c)"
      exec ocm login --token="$OCM_TOKEN" --url="$OCM_ENV"
      '
}

ocm_oc_login() {
    osd_cluster_name=$1

    export PSAP_ODS_SECRET_PATH
    export API_URL=$(ocm describe cluster "$osd_cluster_name" --json | jq -r .api.url)

    # do it in a subshell to avoid leaking the `KUBEADMIN_PASS` secret because of `set -x`
    bash -c '
    source "$PSAP_ODS_SECRET_PATH/create_osd_cluster.password"
    oc login "$API_URL" \
             --username=kubeadmin \
             --password="$KUBEADMIN_PASS" \
             --insecure-skip-tls-verify
    '
}

ocm_cluster_is_ready() {
    osd_cluster_name=$1

    [[ $((ocm describe cluster "$osd_cluster_name"  --json || true) | jq -r .state) == "ready" ]];
}

get_osd_cluster_name() {
    cluster_role=$1

    if [[ "${OSD_CLUSTER_NAME}" ]]; then
        echo "$OSD_CLUSTER_NAME"
        return
    fi

    cat "${SHARED_DIR:-}/osd_${cluster_role}_cluster_name" 2>/dev/null || true
}

get_cluster_is_rosa() {
    cluster_role=$1

    if [[ "${OSD_CLUSTER_IS_ROSA}" ]]; then
        echo "$OSD_CLUSTER_IS_ROSA"
        return
    fi

    cat "${SHARED_DIR:-}/osd_${cluster_role}_cluster_is_rosa" 2>/dev/null || true
}

get_notebook_size() {
    cluster_role=$1

    if [[ "$cluster_role" == "sutest" ]]; then
        echo $ODS_NOTEBOOK_CPU_SIZE $ODS_NOTEBOOK_MEMORY_SIZE_GI
    else
        echo $ODS_TESTPOD_CPU_SIZE $ODS_TESTPOD_MEMORY_SIZE_GI
    fi
}

get_compute_node_count() {
    cluster_role=$1
    shift
    cluster_type=$1
    shift
    instance_type=$1
    shift

    if [[ "$cluster_role" == "sutest" && "$SUTEST_FORCE_COMPUTE_NODES_COUNT" ]]; then
        echo "$SUTEST_FORCE_COMPUTE_NODES_COUNT"
        return

    elif [[ "$cluster_role" == "driver" && "$DRIVER_FORCE_COMPUTE_NODES_COUNT" ]]; then
        echo "$DRIVER_FORCE_COMPUTE_NODES_COUNT"
        return

    elif [[ "$cluster_role" == "sutest" && "$ENABLE_AUTOSCALER" ]]; then
        echo 2
        return
    fi

    notebook_size=$(get_notebook_size "$cluster_role")
    size=$(bash -c "python3 $THIS_DIR/sizing/sizing '$instance_type' '$ODS_CI_NB_USERS' $notebook_size >&2 > '${ARTIFACT_DIR:-/tmp}/${cluster_role}_${cluster_type}_sizing'; echo \$?")

    if [[ "$size" == 0 ]]; then
        echo "ERROR: couldn't determine the number of nodes to request ..." >&2
        false
    fi

    echo "$size"
}

get_compute_node_type() {
    cluster_role=$1
    shift
    cluster_type=$1

    if [[ "$cluster_role" == "sutest" ]]; then
        if [[ "$cluster_type" == "ocp" ]]; then
            echo "$OCP_SUTEST_COMPUTE_MACHINE_TYPE"
        else
            echo "$OSD_SUTEST_COMPUTE_MACHINE_TYPE"
        fi
    else
        echo "$DRIVER_COMPUTE_MACHINE_TYPE"
    fi
}
