#! /bin/bash -e

THIS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
source ${THIS_DIR}/../_common.sh

DEPLOY_FROM_BUNDLE_FLAG="--from-bundle="
DEPLOY_ONLY_CLUSTERPOLICY_FLAG="--only-clusterpolicy"

usage() {
    cat <<EOF
Deploys the GPU Operator from OperatorHub / OLM

Usage:
    $0
    $0 <version> [<channel>]
    $0 $DEPLOY_FROM_BUNDLE_FLAG
    $0 $DEPLOY_ONLY_CLUSTERPOLICY_FLAG

Flags:
  -h, --help           Display this help message

  ${DEPLOY_FROM_BUNDLE_FLAG}master Deploy the current master-branch version from the bundle image
                       See roles/gpu_operator_deploy_from_operatorhub/defaults/main/bundle.yml for the image path.
  ${DEPLOY_FROM_BUNDLE_FLAG}<path> Deploy the from the given bundle image
  $DEPLOY_ONLY_CLUSTERPOLICY_FLAG Do not deploy the operator itself, only create the ClusterPolicy from the CSV.
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

if [ "$#" -gt 1 ]; then
    echo "FATAL: expected 0 or 1 parameter ... (got '$@')"
    usage
    exit 1
elif [[ "${1:-}" == "$DEPLOY_FROM_BUNDLE_FLAG"* ]]; then
    ANSIBLE_OPTS="${ANSIBLE_OPTS} -e gpu_operator_deploy_from=bundle"

    bundle=${1##$DEPLOY_FROM_BUNDLE_FLAG}
    if [[ "$bundle" == "master" ]]; then
        echo "Deploying the GPU Operator from OperatorHub using its master bundle."
    else
        echo "Deploying the GPU Operator from OperatorHub using bundle at $bundle."
        ANSIBLE_OPTS="${ANSIBLE_OPTS} -e deploy_bundle_image=$bundle"
    fi

elif [[ "${1:-}" == "$DEPLOY_ONLY_CLUSTERPOLICY_FLAG" ]]; then
    ANSIBLE_OPTS="${ANSIBLE_OPTS} -e gpu_operator_deploy_from=pre-deployed"
    echo "Not deploying the GPU Operator, only create the ClusterPolicy from the CSV."
elif [[ "${1:-}" == "-"* ]]; then
    echo "FATAL: unexpected parameters ... ($@)"
    usage
    exit 1
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
