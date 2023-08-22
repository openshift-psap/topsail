#! /bin/bash

set -o pipefail
set -o errexit
set -o nounset
set -o errtrace
set -x

# based on https://github.com/opendatahub-io/caikit-tgis-serving/blob/8e9104109bb1bc79e57bc50933dc7363b73f5715/demo/kserve/Kserve.md
# and https://github.com/opendatahub-io/caikit-tgis-serving/blob/8e9104109bb1bc79e57bc50933dc7363b73f5715/demo/kserve/scripts/install/kserve-install.sh

ARTIFACT_DIR=${ARTIFACT_DIR:-/tmp}
GIT_REPO=opendatahub-io/caikit-tgis-serving
GIT_REF=main

export TARGET_OPERATOR=brew # Set this among odh, rhods or brew, if you want to skip the question in the script.
export CHECK_UWM=false # Set this to "false", if you want to skip the User Workload Configmap check message

# Enable User Workload Monitoring
# Configure User Workload Monitoring

cat <<EOF | oc apply -f-
apiVersion: v1
kind: ConfigMap
metadata:
  name: user-workload-monitoring-config
  namespace: openshift-user-workload-monitoring
data:
  config.yaml: |
    prometheus:
      logLevel: debug
      retention: 15d #Change as needed
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: cluster-monitoring-config
  namespace: openshift-monitoring
data:
  config.yaml: |
    enableUserWorkload: true
EOF

TOPSAIL_DIR=$(pwd)

rm -rf /tmp/caikit-tgis-serving /tmp/kserve

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
    go run $TOPSAIL_DIR/testing/watsonx-serving/poc/cert/gen-cert.go ${COMMON_NAME} ${BASE_CERT_DIR}
}

generate_certs

cd /tmp
git clone --quiet https://github.com/$GIT_REPO

cd caikit-tgis-serving/demo/kserve
git fetch --quiet origin "$GIT_REF"
git checkout FETCH_HEAD

git show --no-patch | tee $ARTIFACT_DIR/caikit-tgis-serving.commit

cp ${TOPSAIL_DIR}/testing/watsonx-serving/poc/{kserve-install.sh,deploy-minio.sh} \
   scripts/install/

cp ${TOPSAIL_DIR}/testing/watsonx-serving/poc/deploy-model.sh \
   scripts/test/

bash -ex scripts/install/kserve-install.sh
bash -ex scripts/install/deploy-minio.sh
