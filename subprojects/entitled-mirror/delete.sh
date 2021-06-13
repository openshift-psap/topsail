#!/bin/bash

set -euxo pipefail

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")

source ${SCRIPT_DIR}/config.env

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
