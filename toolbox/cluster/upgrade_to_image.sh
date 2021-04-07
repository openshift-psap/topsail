#! /bin/bash -e

THIS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
source ${THIS_DIR}/../_common.sh

if [ -z "${1-}" ]; then
    echo "FATAL: An image must be provided to upgrade the cluster..."
    exit 1
fi

ANSIBLE_OPTS="${ANSIBLE_OPTS} -e cluster_upgrade_image=${1}"

exec ansible-playbook ${ANSIBLE_OPTS} playbooks/cluster_upgrade_to_image.yml
