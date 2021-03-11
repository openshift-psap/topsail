#! /bin/bash -e

THIS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
source ${THIS_DIR}/_common.sh

if [ ! -z "${1-}" ]; then
    echo "Using machine_instance_type"
    ANSIBLE_OPTS="${ANSIBLE_OPTS} -e machine_instance_type=${1}"
fi

exec ansible-playbook ${ANSIBLE_OPTS} playbooks/scaleup-cluster.yml
