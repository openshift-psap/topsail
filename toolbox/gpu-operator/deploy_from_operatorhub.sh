#! /bin/bash -e

THIS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
source ${THIS_DIR}/../_common.sh

ANSIBLE_OPTS="${ANSIBLE_OPTS} -e install_nfd_operator_from_hub=no"
ANSIBLE_OPTS="${ANSIBLE_OPTS} -e install_gpu_operator_from_hub=yes"
ANSIBLE_OPTS="${ANSIBLE_OPTS} -e undeploy_gpu_operator=no"
ANSIBLE_OPTS="${ANSIBLE_OPTS} -e user_mode=not-ci"

if [ "$#" -gt 1 ]; then
    echo "FATAL: expected 0 or 1 parameter ... (got '$@')"
    echo "Usage: $0 [gpu_operator_operatorhub_version]"
    exit 1
elif [ "$#" -eq 1 ]; then
    ANSIBLE_OPTS="${ANSIBLE_OPTS} -e gpu_operator_operatorhub_version=$1"
    echo "Deploying the GPU Operator from OperatorHub using version '$1'."
else
    echo "Deploying the GPU Operator from OperatorHub using the latest version available."
fi

exec ansible-playbook ${ANSIBLE_OPTS} playbooks/deploy-gpu-operator-from-operatorhub.yml
