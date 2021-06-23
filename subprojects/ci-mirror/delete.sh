#!/bin/bash

set -euo pipefail

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")

if [[ ${NAMESPACE:-} == "" ]]; then
    echo Please source a mirror configuration file before running this script
    exit 1
fi

set -x

# This script intentionally doesn't delete the PVC because
# syncing the repo takes a long time
oc delete -n ${NAMESPACE} \
    deployment/${NAME} \
    route/${NAME} \
    service/${NAME} \
    secret/${NAME}-client-auth \
    secret/${NAME}-acme \
    serviceaccount/${NAME} \
    securitycontextconstraints.security.openshift.io/${NAME}
