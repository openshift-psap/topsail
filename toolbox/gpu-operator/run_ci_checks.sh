#! /bin/bash -e

THIS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
source ${THIS_DIR}/../_common.sh

ANSIBLE_OPTS="${ANSIBLE_OPTS} -e install_nfd_operator_from_hub=no"
ANSIBLE_OPTS="${ANSIBLE_OPTS} -e install_gpu_operator_from_hub=no"
ANSIBLE_OPTS="${ANSIBLE_OPTS} -e user_mode=ci"

exec ansible-playbook ${ANSIBLE_OPTS} playbooks/deploy-gpu-operator-from-operatorhub.yml
