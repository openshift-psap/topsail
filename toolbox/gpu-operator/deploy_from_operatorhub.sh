#! /bin/bash -e

THIS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
source ${THIS_DIR}/../_common.sh

DEPLOY_FROM_BUNDLE_FLAG="--from-bundle=master"

usage() {
    cat <<EOF
Usage: $0 [FLAG]
Deploys the GPU Operator from OperatorHub / OLM

Flags:
  -h, --help           Display this help message

  $DEPLOY_FROM_BUNDLE_FLAG Deploy the current master-branch version from the bundle image
                       See roles/gpu_operator_deploy_from_operatorhub/defaults/main/bundle.yml for the image path.

  <empty>              Deploy the latest version available in OperatorHub

  <version>            Deploy a given version from OperatorHub
                       See toolbox/gpu-operator/list_version_from_operator_hub.sh for the version available
EOF
}

if [[ "${1:-}" == "--help" || "${1:-}" == -h ]]; then
    usage
    exit 0
fi

if [ "$#" -gt 1 ]; then
    echo "FATAL: expected 0 or 1 parameter ... (got '$@')"
    usage
    exit 1
elif [[ "${1:-}" == "$DEPLOY_FROM_BUNDLE_FLAG" ]]; then
    echo "Deploying the GPU Operator from OperatorHub using its master bundle."
    ANSIBLE_OPTS="${ANSIBLE_OPTS} -e gpu_operator_deploy_from=bundle"

elif [[ "$#" == 1 ]]; then
    ANSIBLE_OPTS="${ANSIBLE_OPTS} -e gpu_operator_operatorhub_version=$1"
    echo "Deploying the GPU Operator from OperatorHub using version '$1'."
else
    echo "Deploying the GPU Operator from OperatorHub using the latest version available."
fi

exec ansible-playbook ${ANSIBLE_OPTS} playbooks/gpu_operator_deploy_from_operatorhub.yml
