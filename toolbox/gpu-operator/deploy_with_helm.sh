#! /bin/bash -e

THIS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
source ${THIS_DIR}/../_common.sh

source ${THIS_DIR}/_helm_common.sh

oc create namespace $OPERATOR_NAMESPACE || true

exec bash ./roles/nv_gpu_install_from_commit/files/helm_deploy_operator.sh deploy_from_helm "$@"
