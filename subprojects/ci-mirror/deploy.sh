#!/bin/bash

set -euo pipefail

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")

if [[ ${NAMESPACE:-} == "" ]]; then
    echo Please source a mirror configuration file before running this script
    exit 1
fi

if [[ "${NAMESPACE}" == ci-entitled-mirror ]]; then
    if ! oc get nodes -lentitled=true -oname; then
        echo "Please entitle one of the cluster nodes and give it an entitled=true label"
        exit 1
    fi
fi

set -x

oc process -f ${SCRIPT_DIR}/openshift/template.yaml \
    -p NAME=${NAME} \
    -p NAMESPACE=${NAMESPACE} \
    -p QUAY_REPO=${QUAY_REPO} \
    -p PVC_SIZE=${PVC_SIZE} \
    -p "CLIENT_CA=$( < ./generated_auth/generated_ca.crt base64 --wrap=0 )" \
    -p "NGINX_CONFIG=$( < ${NGINX_CONF} base64 --wrap=0 )" \
    -p "SYNC_COMMANDS=$( < ${SYNC_SCRIPT} base64 --wrap=0 )" \
    | oc apply -f -
