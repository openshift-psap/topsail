#! /bin/bash -e

THIS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
source ${THIS_DIR}/../_common.sh

usage() {
    echo "Usage: $0 </path/to/key.pem>"
}

if ! [ "$#" -eq 1 ]; then
    echo "ERROR: please pass a PEM key as argument."
    usage
    exit 1
fi

PEM_KEY="$(realpath "$1")"
if ! [ -e $PEM_KEY ]; then
    echo "ERROR: Cannot access $1 ($PEM_KEY) file."
    exit 1
fi

ANSIBLE_OPTS="${ANSIBLE_OPTS} -e entitlement_pem=$PEM_KEY"

exec ansible-playbook ${ANSIBLE_OPTS} playbooks/entitlement_test_in_cluster.yml
