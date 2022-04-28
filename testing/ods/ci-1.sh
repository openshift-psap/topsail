#! /bin/bash

set -o errexit
set -o pipefail
set -o nounset
set -x

#PSAP_ODS_SECRET_PATH="/var/run/psap-ods-secret-1"
PSAP_ODS_SECRET_PATH="/var/run/psap-entitlement-secret"
S3_LDAP_PROPS="${PSAP_ODS_SECRET_PATH}/s3_ldap.passwords"

ODS_CATALOG_VERSION="quay.io/modh/qe-catalog-source"
ODS_CATALOG_IMAGE_VERSION="v160-8"

ODS_CI_TEST_NAMESPACE=loadtest
ODS_CI_REPO="https://github.com/openshift-psap/ods-ci.git"
ODS_CI_REF="multiuser"

ODS_CI_IMAGESTREAM="ods-ci"
ODS_CI_TAG="latest"

ODS_CI_NB_USERS=5
ODS_CI_USER_PREFIX=testuser

ODS_CI_USER_GROUP=rhods-users

oc_adm_groups_new_rhods_users() {
    group=$1
    shift
    user_prefix=$1
    shift
    nb_users=$1

    echo "Adding $nb_users user with prefix '$user_prefix' in the group '$group' ..."
    users=$(for i in $(seq 0 $nb_users); do echo ${user_prefix}$i; done)
    oc adm groups new $group $(echo $users)
}

# ---

oc create namespace "$ODS_CI_TEST_NAMESPACE"

./run_toolbox.py utils build_push_image \
                 "${ODS_CI_IMAGESTREAM}" "$ODS_CI_TAG" \
                 --namespace="$ODS_CI_TEST_NAMESPACE" \
                 --git-repo="$ODS_CI_REPO" \
                 --git-ref="$ODS_CI_REF" \
                 --context-dir="/" \
                 --dockerfile-path="build/Dockerfile"

# no need to add machines, there's already 2 workers in the CI cluster
#./run_toolbox.py cluster set-scale m5.xlarge 2

./run_toolbox.py rhods deploy_ldap "$ODS_CI_USER_PREFIX" "$ODS_CI_NB_USERS" "$S3_LDAP_PROPS"

./run_toolbox.py cluster deploy_minio_s3_server "$S3_LDAP_PROPS"

echo "Deploying ODS $ODS_CATALOG_IMAGE_VERSION (from $ODS_CATALOG_VERSION)"
./run_toolbox.py rhods deploy_ods "$ODS_CATALOG_VERSION" "$ODS_CATALOG_IMAGE_VERSION"

oc_adm_groups_new_rhods_users "$ODS_CI_USER_GROUP" "$ODS_CI_USER_PREFIX" "$ODS_CI_NB_USERS"

./run_toolbox.py rhods test_jupyterlab "$ODS_CI_USER_PREFIX" "$ODS_CI_NB_USERS" "$S3_LDAP_PROPS"
