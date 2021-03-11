#! /bin/bash -e

THIS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
source ${THIS_DIR}/../_common.sh

if [ "$#" -lt 2 ]; then
    set +x
    echo "Usage:   $0 <ci command> <git repository> <git reference> [gpu_operator_image_tag_uid]"
    echo "Example: $0 'run gpu-ci' https://github.com/openshift-psap/ci-artifacts.git master"
    exit 1
fi

ci_command=$1
git_repo=$2
git_ref=$3

if [ "$#" -eq 4 ]; then
    image_tag_uid=$4
else
    image_tag_uid=$(cat /proc/sys/kernel/random/uuid | cut -b-8)
fi

echo "Using Git repository ${git_repo} with ref ${git_ref} and tag_uid ${image_tag_uid}"
echo "CI command to run: '$ci_command'"

ANSIBLE_OPTS="${ANSIBLE_OPTS} -e local_ci_git_repo=${git_repo}"
ANSIBLE_OPTS="${ANSIBLE_OPTS} -e local_ci_git_ref=${git_ref}"
ANSIBLE_OPTS="${ANSIBLE_OPTS} -e local_ci_image_tag_uid=${image_tag_uid}"

ANSIBLE_OPTS="${ANSIBLE_OPTS} -e local_ci_deploy=yes"
ANSIBLE_OPTS="${ANSIBLE_OPTS} -e local_ci_undeploy=no"

export LOCAL_CI_COMMAND="$ci_command"

exec ansible-playbook ${ANSIBLE_OPTS} playbooks/build-psap-ci.yml
