#!/bin/bash

set -o pipefail
set -o errexit
set -o nounset
set -o errtrace
set -x

# running from opendatahub-io/caikit-tgis-serving::scripts/test/deploy-minio.sh

source "$(dirname "$(realpath "$0")")/../env.sh"

# Deploy Minio

bash -ec '
        echo "Preparing the secret key ..."
        ACCESS_KEY_ID=THEACCESSKEY
        SECRET_ACCESS_KEY=$(openssl rand -hex 32)

        cat ./custom-manifests/minio/minio.yaml \
          | sed "s/<accesskey>/$ACCESS_KEY_ID/g"  \
          | sed "s+<secretkey>+$SECRET_ACCESS_KEY+g" \
          > ${BASE_DIR}/minio-current.yaml

        cat ./custom-manifests/minio/minio-secret.yaml \
          | sed "s/<accesskey>/$ACCESS_KEY_ID/g" \
          | sed "s+<secretkey>+$SECRET_ACCESS_KEY+g" \
          | sed "s/<minio_ns>/$MINIO_NS/g" \
          > ${BASE_DIR}/minio-secret-current.yaml
'

oc create ns ${MINIO_NS} --dry-run=client -oyaml | oc apply -f-

oc delete -n ${MINIO_NS} -f ${BASE_DIR}/minio-current.yaml --ignore-not-found
oc create -n ${MINIO_NS} -f ${BASE_DIR}/minio-current.yaml

oc delete -n ${MINIO_NS} -f ${BASE_DIR}/minio-secret-current.yaml --ignore-not-found
oc create -n ${MINIO_NS} -f ${BASE_DIR}/minio-secret-current.yaml
