#! /bin/bash -e

THIS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
source ${THIS_DIR}/_common.sh

exec ansible-playbook ${INVENTORY_ARG} ${ANSIBLE_OPTS} playbooks/scaleup-gpu-node.yml
