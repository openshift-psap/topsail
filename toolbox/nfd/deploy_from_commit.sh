#! /bin/bash -e

THIS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
source ${THIS_DIR}/../_common.sh

usage() {
    cat <<EOF
Deploys the NFD operator from target Git repo and branch

Usage:
    $0 [FLAG] <git repository> <git reference> [nfd_operator_image_tag]

Example:
    https://github.com/openshift/cluster-nfd-operator.git master

Flags:
  -h, --help           Display this help message
EOF
}

if [[ "${1:-}" == "--help" || "${1:-}" == -h ]]; then
    usage
    exit 0
fi

if [ "$#" -lt 2 ]; then
    usage
    exit 1
fi

# Set vars
git_repo=$1
git_ref=$2
image_tag=$3

ANSIBLE_OPTS="${ANSIBLE_OPTS} -e nfd_operator_git_repo=${git_repo}"
ANSIBLE_OPTS="${ANSIBLE_OPTS} -e nfd_operator_git_ref=${git_ref}"
ANSIBLE_OPTS="${ANSIBLE_OPTS} -e nfd_operator_image_tag=${image_tag}"

exec ansible-playbook ${ANSIBLE_OPTS} playbooks/nfd_operator_deploy_custom_commit.yml
