#!/bin/bash

set -euxo pipefail

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")

source ${SCRIPT_DIR}/config.env

if ! oc get nodes -lentitled=true -oname; then
    echo "Please entitle one of the cluster nodes and give it an entitled=true label"
    exit 1
fi

oc process -f ${SCRIPT_DIR}/openshift/template.yaml \
    -p NAME=${NAME} \
    -p NAMESPACE=${NAMESPACE} \
    -p QUAY_REPO=${QUAY_REPO} \
    -p "CLIENT_CA=$( < ./auth/ca/generated_ca.crt base64 --wrap=0 )" \
    -p "NGINX_CONFIG=$( < ./containers/serve/nginx.conf base64 --wrap=0 )" \
    -p "SYNC_COMMANDS=$( < ./containers/sync/sync_commands.sh base64 --wrap=0 )" \
    | oc apply -f -
