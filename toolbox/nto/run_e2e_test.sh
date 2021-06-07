#! /bin/bash -e

THIS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
source ${THIS_DIR}/../_common.sh

git_repo=${1:-https://github.com/openshift/cluster-node-tuning-operator.git}
git_ref=${2:-}

test "$git_ref" || {
    git_ref=origin/release-$(oc get clusterversion -o jsonpath='{.items[].status.desired.version}' | grep -Po '^\d+\.\d+')
}

ANSIBLE_OPTS="${ANSIBLE_OPTS} -e nto_git_repo=${git_repo}"
ANSIBLE_OPTS="${ANSIBLE_OPTS} -e nto_git_ref=${git_ref}"

exec ansible-playbook ${ANSIBLE_OPTS} playbooks/nto_run_e2e_test.yml
