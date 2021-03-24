#! /bin/bash -e

THIS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
source ${THIS_DIR}/../_common.sh

if [ "${1-}" ]; then
    echo "Using '$1' machine-type to scale-up the cluster"
    ANSIBLE_OPTS="${ANSIBLE_OPTS} -e cluster_scaleup_machine_instance_type=${1}"
fi

exec ansible-playbook ${ANSIBLE_OPTS} playbooks/cluster_scaleup.yml
