#! /bin/bash -e

THIS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
source ${THIS_DIR}/../_common.sh

DEPLOY_FROM_BUNDLE_FLAG="--from-bundle=master"

usage() {
    cat <<EOF
Deploys the GPU Operator from OperatorHub / OLM

Usage:
    $0
    $0 <version> [<channel>]
    $0 $DEPLOY_FROM_BUNDLE_FLAG

Flags:
  -h, --help           Display this help message

  $DEPLOY_FROM_BUNDLE_FLAG Deploy the current master-branch version from the bundle image
                       See roles/gpu_operator_deploy_from_operatorhub/defaults/main/bundle.yml for the image path.

  <empty>              Deploy the latest version available in OperatorHub

  <version>            Deploy a given version from OperatorHub
                       See toolbox/gpu-operator/list_version_from_operator_hub.sh for the version available

  <channel>            Channel to use when deploying from OperatorHub. Default: stable
EOF
}

if [[ "${1:-}" == "--help" || "${1:-}" == -h ]]; then
    usage
    exit 0
fi

if [[ "${1:-}" == "$DEPLOY_FROM_BUNDLE_FLAG" ]]; then
    echo "Deploying the GPU Operator from OperatorHub using its master bundle."
    ANSIBLE_OPTS="${ANSIBLE_OPTS} -e gpu_operator_deploy_from=bundle"

    if [ "$#" -gt 1 ]; then
        shift
        echo "FATAL: $DEPLOY_FROM_BUNDLE_FLAG expects no additional parameter (got '$@')"
        usage
        exit 1
    fi
elif [[ "$#" == 0 ]]; then
    echo "Deploying the GPU Operator from OperatorHub using the latest version available."
elif [[ "$#" == 1 || "$#" == 2 ]]; then
    ANSIBLE_OPTS="${ANSIBLE_OPTS} -e gpu_operator_operatorhub_version=$1"
    echo "Deploying the GPU Operator from OperatorHub using version '$1'."
    if [[ "$#" == 2 ]]; then
        ANSIBLE_OPTS="${ANSIBLE_OPTS} -e gpu_operator_operatorhub_channel=$2"
        echo "Deploying the GPU Operator from OperatorHub using channel '$2'."
    fi
else
    echo "FATAL: unexpected number of paramters (got '$@')"
    usage
    exit 1
fi

exec ansible-playbook ${ANSIBLE_OPTS} playbooks/gpu_operator_deploy_from_operatorhub.yml
