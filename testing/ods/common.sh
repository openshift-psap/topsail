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
OSD_USE_ODS_CATALOG=1

ODS_QE_CATALOG_IMAGE="quay.io/modh/qe-catalog-source"
ODS_QE_CATALOG_IMAGE_TAG="v1100-6"

ODS_CI_TEST_NAMESPACE=loadtest
ODS_CI_REPO="https://github.com/openshift-psap/ods-ci.git"
ODS_CI_REF="jh-at-scale"

ODS_CI_IMAGESTREAM="ods-ci"
ODS_CI_TAG="latest"

ODS_CI_NB_USERS=10
ODS_CI_USER_PREFIX=testuser

if [[ "$OSD_USE_ODS_CATALOG" == "0" ]]; then
    # deploying from the addon. Get the email address from the secret vault.
    ODS_ADDON_EMAIL_ADDRESS=$(cat "$PSAP_ODS_SECRET_PATH/addon.email")
fi

LDAP_IDP_NAME=RHODS_CI_LDAP

CLUSTER_NAME_PREFIX=odsci

OSD_COMPUTE_MACHINE_TYPE=m5.xlarge
OSD_COMPUTE_NODES=7
OSD_VERSION=4.10.15
OSD_REGION=us-west-2

OCP_VERSION=4.10.15
OCP_REGION=us-west-2
OCP_MASTER_MACHINE_TYPE=m5.xlarge
OCP_WORKER_MACHINE_TYPE=m5.xlarge
OCP_WORKER_NODES=7
OCP_BASE_DOMAIN=psap.aws.rhperfscale.org

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

    cat "$SHARED_DIR/osd_${cluster_role}_cluster_name" 2>/dev/null || true
}
