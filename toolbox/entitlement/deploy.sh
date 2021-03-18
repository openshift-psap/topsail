#! /bin/bash -e

CURR_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
source ${CURR_DIR}/../_common.sh

usage() {
    echo "Usage: $0 (--pem|--machine-configs) </path/to/file>"
}

if ! [ "$#" -eq 2 ]; then
    echo "ERROR: please pass two arguments."
    usage
    exit 1
fi

if [[ "$1" == "--pem" ]]; then
    ANSIBLE_OPTS="${ANSIBLE_OPTS} -e entitlement_pem=$2"
    echo "Using '$2' as PEM key"
elif [[ "$1" == "--machine-configs" ]]; then
    ANSIBLE_OPTS="${ANSIBLE_OPTS} -e entitlement_resources=$2"
    echo "Using '$2' as entitlement resources"
else
    echo "ERROR: please pass a valid flag."
    usage
    exit 1
fi

exec ansible-playbook ${ANSIBLE_OPTS} playbooks/entitlement_deploy.yml
