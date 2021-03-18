#! /bin/bash -e

CURR_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

source ${CURR_DIR}/../_common.sh

exec ansible-playbook ${ANSIBLE_OPTS} playbooks/entitlement_undeploy.yml
