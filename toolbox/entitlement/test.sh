#! /bin/bash -e

THIS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
source ${THIS_DIR}/../_common.sh

ANSIBLE_OPTS="${ANSIBLE_OPTS} -e entitlement_deploy=no"
ANSIBLE_OPTS="${ANSIBLE_OPTS} -e entitlement_test=yes"
ANSIBLE_OPTS="${ANSIBLE_OPTS} -e entitlement_test_wait=no"

exec ansible-playbook ${INVENTORY_ARG} ${ANSIBLE_OPTS} playbooks/entitlement.yml
