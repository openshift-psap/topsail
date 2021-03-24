#! /bin/bash -e

THIS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
source ${THIS_DIR}/../_common.sh

source ${THIS_DIR}/_helm_common.sh

set -x

if ! oc get namespace/$OPERATOR_NAMESPACE >/dev/null 2>/dev/null; then
    oc create namespace $OPERATOR_NAMESPACE
fi

exec bash ./roles/nv_gpu_install_from_commit/files/helm_deploy_operator.sh deploy_from_helm "$@"
