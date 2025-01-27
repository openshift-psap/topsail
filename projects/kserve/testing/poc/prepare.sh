#! /bin/bash

set -o pipefail
set -o errexit
set -o nounset
set -o errtrace
set -x

# based on https://github.com/opendatahub-io/caikit-tgis-serving/blob/8e9104109bb1bc79e57bc50933dc7363b73f5715/demo/kserve/Kserve.md
# and https://github.com/opendatahub-io/caikit-tgis-serving/blob/8e9104109bb1bc79e57bc50933dc7363b73f5715/demo/kserve/scripts/install/kserve-install.sh

ARTIFACT_DIR=${ARTIFACT_DIR:-/tmp}

export TARGET_OPERATOR=brew # Set this among odh, rhods or brew, if you want to skip the question in the script.
export CHECK_UWM=false # Set this to "false", if you want to skip the User Workload Configmap check message
export deploy_odh_operator=false

TOPSAIL_DIR=$(pwd)

rm -rf /tmp/kserve

generate_certs() {
    BASE_CERT_DIR=/tmp/kserve/certs

    mkdir -p $BASE_CERT_DIR

    # base on:
    # https://github.com/opendatahub-io/caikit-tgis-serving/blob/main/demo/kserve/scripts/generate-wildcard-certs.sh
    # Generate wildcard cert for a gateway.
    export DOMAIN_NAME=$(oc get ingresses.config.openshift.io cluster -o jsonpath='{.spec.domain}' | awk -F'.' '{print $(NF-1)"."$NF}')
    export COMMON_NAME=$(oc get ingresses.config.openshift.io cluster -o jsonpath='{.spec.domain}'|sed 's/apps.//')

    # openssl req -x509 -sha256 -nodes -days 365 -newkey rsa:2048 \
    #         -subj "/O=Example Inc./CN=${DOMAIN_NAME}" \
    #         -keyout $BASE_DIR/root.key \
    #         -out $BASE_DIR/root.crt

    # openssl req -nodes -newkey rsa:2048 \
    #         -subj "/CN=*.${COMMON_NAME}/O=Example Inc." \
    #         -keyout $BASE_CERT_DIR/wildcard.key \
    #         -out $BASE_CERT_DIR/wildcard.csr

    # openssl x509 -req -days 365 -set_serial 0 \
    #         -CA $BASE_CERT_DIR/root.crt \
    #         -CAkey $BASE_CERT_DIR/root.key \
    #         -in $BASE_CERT_DIR/wildcard.csr \
    #         -out $BASE_CERT_DIR/wildcard.crt

    # openssl x509 -in ${BASE_CERT_DIR}/wildcard.crt -text

    # ^^^ this doesn't work when the DOMAINE_NAME is too long (>64b)

    export GOROOT=/usr/lib/golang/
    go run $TOPSAIL_DIR/projects/kserve/testing/poc/cert/gen-cert.go ${COMMON_NAME} ${BASE_CERT_DIR}
}

# generate_certs

cd "${TOPSAIL_DIR}/projects/kserve/testing/poc/"
ln -sf poc/env.sh ..
ln -sf poc/utils.sh ..

# delete all the DataScienceCluster resources except the default one
dsclusters=$(oc get datasciencecluster -oname | grep -v /default || true)
if [[ -n "$dsclusters" ]]; then
    oc delete $dsclusters
fi

bash -ex kserve-install.sh
