#! /bin/bash -e

CURR_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
source ${CURR_DIR}/../_common.sh

usage() {
    cat <<EOF
Deploys a cluster-wide entitlement key & RHSM config file
(and optionally a YUM repo certificate) with the help of
MachineConfig resources.

Usage: $0 --pem <pem_key> [--ca <pem_ca>]

Arguments:
     --pem <pem_key>   Deploy <pem_key> PEM key and RHSM config file on the cluster
     --ca <pem_ca>     Deploy <pem_ca> CA PEM key on the cluster
EOF
    echo ""
}

if ! [[ "$#" -eq 2 || "$#" -eq 4 ]]; then
    echo "ERROR: please pass two or four arguments."
    usage
    exit 1
fi

if [[ "$1" == "--pem" ]]; then
    ANSIBLE_OPTS="${ANSIBLE_OPTS} -e entitlement_pem=$(realpath $2)"
    echo "Using '$2' as PEM key"
else
    echo "ERROR: please pass a valid flag."
    usage
    exit 1
fi

if [[ "${3:-}" == "--ca" ]]; then
    ANSIBLE_OPTS="${ANSIBLE_OPTS} -e entitlement_repo_ca=$(realpath $4)"
    echo "Using '$4' as repo CA"
fi

exec ansible-playbook ${ANSIBLE_OPTS} playbooks/entitlement_deploy.yml
