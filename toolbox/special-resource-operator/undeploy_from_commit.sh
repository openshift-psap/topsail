#! /bin/bash -e

THIS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
source ${THIS_DIR}/../_common.sh

if [ "$#" -lt 2 ]; then
    echo "Usage:   $0 <git repository> <git reference>"
    echo "Example: $0 https://github.com/openshift-psap/special-resource-operator.git master"
    exit 1
fi
git_repo=$1
git_ref=$2

ANSIBLE_OPTS="${ANSIBLE_OPTS} -e sro_git_repo=${git_repo}"
ANSIBLE_OPTS="${ANSIBLE_OPTS} -e sro_git_ref=${git_ref}"

exec ansible-playbook ${ANSIBLE_OPTS} playbooks/sro_undeploy_custom_commit.yml
