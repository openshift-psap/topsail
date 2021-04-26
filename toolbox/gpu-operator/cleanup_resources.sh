#! /bin/bash -e

THIS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
source ${THIS_DIR}/../_common.sh

source ${THIS_DIR}/_helm_common.sh

set +e
toolbox/gpu-operator/undeploy_from_operatorhub.sh
toolbox/gpu-operator/undeploy_from_helm.sh

bash "${HELM_DEPLOY_OPERATOR}" cleanup

echo "All the GPU Operator resources should have been deleted!"
