#! /bin/bash -e

THIS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
source ${THIS_DIR}/../_common.sh

source ${THIS_DIR}/_helm_common.sh

set -x

if ! oc get namespace/$OPERATOR_NAMESPACE >/dev/null 2>/dev/null; then
    oc create namespace $OPERATOR_NAMESPACE
fi

exec bash "${HELM_DEPLOY_OPERATOR}" deploy_from_helm "$@"
