#! /bin/bash -e

THIS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
source ${THIS_DIR}/../_common.sh

if [ "$#" -gt 1 ]; then
    echo "FATAL: expected 0 or 1 parameter ... (got '$@')"
    echo "Usage: $0 [nfd_operatorhub_channel, eg: 4.7]"
    exit 1
elif [ "$#" -eq 1 ]; then
    ANSIBLE_OPTS="${ANSIBLE_OPTS} -e nfd_channel=$1"
    echo "Deploying the NFD Operator from OperatorHub using channel '$1'."
fi

exec ansible-playbook ${ANSIBLE_OPTS} playbooks/nfd_operator_deploy_from_operatorhub.yml
