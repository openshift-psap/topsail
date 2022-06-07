PSAP_ODS_SECRET_PATH="/var/run/psap-ods-secret-1"

OCM_ENV=staging

S3_LDAP_PROPS="${PSAP_ODS_SECRET_PATH}/s3_ldap.passwords"

ODS_CATALOG_VERSION="quay.io/modh/qe-catalog-source"
ODS_CATALOG_IMAGE_VERSION="v1100-6"

ODS_CI_TEST_NAMESPACE=loadtest
ODS_CI_REPO="https://github.com/openshift-psap/ods-ci.git"
ODS_CI_REF="multiuser"

ODS_CI_IMAGESTREAM="ods-ci"
ODS_CI_TAG="latest"

ODS_CI_NB_USERS=10
ODS_CI_USER_PREFIX=testuser

LDAP_IDP_NAME=RHODS_CI_LDAP

CLUSTER_NAME_PREFIX=odsci

OSD_COMPUTE_MACHINE_TYPE=m5.xlarge
OSD_COMPUTE_NODES=7
OSD_VERSION=4.10.15
OSD_REGION=us-west-2

ocm_login() {
    export OCM_ENV
    export PSAP_ODS_SECRET_PATH

    # do it in a subshell to avoid leaking the `OCM_TOKEN` secret because of `set -x`
    bash -c '
      set -o errexit
      set -o nounset

      OCM_TOKEN=$(cat "$PSAP_ODS_SECRET_PATH/ocm.token" | grep "^${OCM_ENV}=" | cut -d= -f2-)
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
    if [[ ! -f "$SHARED_DIR/osd_cluster_name" ]]; then
        return
    fi
    cat "$SHARED_DIR/osd_cluster_name"
}
