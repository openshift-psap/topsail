if [[ -z "${PSAP_ODS_SECRET_PATH:-}" ]]; then
    echo "ERROR: the PSAP_ODS_SECRET_PATH was not provided"
    false # can't exit here
elif [[ ! -d "$PSAP_ODS_SECRET_PATH" ]]; then
    echo "ERROR: the PSAP_ODS_SECRET_PATH does not point to a valid directory"
    false # can't exit here
fi

OCM_ENV=staging # The valid aliases are 'production', 'staging', 'integration'

S3_LDAP_PROPS="${PSAP_ODS_SECRET_PATH}/s3_ldap.passwords"

# if 1, use the ODS_QE_CATALOG_IMAGE OLM catalog.
# Otherwise, install RHODS from OCM addon.
OSD_USE_ODS_CATALOG=${OSD_USE_ODS_CATALOG:-1}

# If the value is set, consider SUTEST to be running on OSD and
# use this cluster name to configure LDAP and RHODS
# Notes
# * KEEP EMPTY IF SUTEST IS NOT ON OSD
# * KEEP EMPTY ON CI, OSD OR OCP ALIKE
OSD_CLUSTER_NAME=

ODS_QE_CATALOG_IMAGE="quay.io/modh/qe-catalog-source"
ODS_QE_CATALOG_IMAGE_TAG="latest"

RHODS_NOTEBOOK_IMAGE_NAME=s2i-generic-data-science-notebook

ODS_CI_TEST_NAMESPACE=loadtest
ODS_CI_REPO="https://github.com/openshift-psap/ods-ci.git"
ODS_CI_REF="jh-at-scale.v220901"

ODS_CI_IMAGESTREAM="ods-ci"
ODS_CI_TAG="latest"
ODS_CI_ARTIFACTS_EXPORTER_TAG="artifacts-exporter"
ODS_CI_ARTIFACTS_EXPORTER_DOCKERFILE="testing/ods/images/Containerfile.s3_artifacts_exporter"

LDAP_IDP_NAME=RHODS_CI_LDAP
LDAP_NB_USERS=1000

ODS_CI_NB_USERS=${ODS_CI_NB_USERS:-5} # number of users to simulate
ODS_CI_USER_PREFIX=psapuser
ODS_NOTEBOOK_SIZE=default # needs to match what the ROBOT test-case requests
ODS_NOTEBOOK_SIZE_TEST_POD="test_pod" # shouldn't change
ODS_SLEEP_FACTOR=${ODS_SLEEP_FACTOR:-1.0} # how long to wait between user starts.
ODS_CI_ARTIFACTS_COLLECTED=no-image-except-failed-and-zero

STATESIGNAL_REDIS_NAMESPACE=loadtest-redis
NGINX_NOTEBOOK_NAMESPACE=loadtest-notebooks
ODS_NOTEBOOK_NAME=simple-notebook.ipynb
ODS_NOTEBOOK_DIR=${THIS_DIR}/notebooks
ODS_EXCLUDE_TAGS=${ODS_EXCLUDE_TAGS:-None} # tags to exclude when running the robot test case

if [[ "$OSD_USE_ODS_CATALOG" == "0" ]]; then
    # deploying from the addon. Get the email address from the secret vault.
    ODS_ADDON_EMAIL_ADDRESS=$(cat "$PSAP_ODS_SECRET_PATH/addon.email")
fi

CLUSTER_NAME_PREFIX=odsci

OSD_VERSION=4.10.15
OSD_REGION=us-west-2

OCP_VERSION=4.10.15
OCP_REGION=us-west-2
OCP_MASTER_MACHINE_TYPE=m6a.xlarge
OCP_WORKER_MACHINE_TYPE=m6a.xlarge
OCP_WORKER_NODES_COUNT=2

OCP_BASE_DOMAIN=psap.aws.rhperfscale.org

# if not empty, enables auto-scaling in the sutest cluster
ENABLE_AUTOSCALER=

# Shouldn't be the same than OCP worker nodes.

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

get_notebook_size() {
    cluster_role=$1

    if [[ "$cluster_role" == "sutest" ]]; then
        echo "$ODS_NOTEBOOK_SIZE"
    else
        echo "$ODS_NOTEBOOK_SIZE_TEST_POD"
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

    notebook_size_name=$(get_notebook_size "$cluster_role")
    size=$(bash -c "python3 $THIS_DIR/sizing/sizing '$notebook_size_name' '$instance_type' '$ODS_CI_NB_USERS' >&2; echo \$?")

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
