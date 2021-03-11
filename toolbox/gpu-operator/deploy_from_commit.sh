#! /bin/bash -e

THIS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
source ${THIS_DIR}/../_common.sh

if [ "$#" -lt 2 ]; then
    set +x
    echo "Usage:   $0 <git repository> <git reference> [gpu_operator_image_tag_uid]"
    echo "Example: $0 https://github.com/NVIDIA/gpu-operator.git master"
    echo "See 'oc get imagestreamtags -n gpu-operator-ci -oname' for the tag-uid to reuse"
    exit 1
fi
git_repo=$1
git_ref=$2

if [ "$#" -eq 3 ]; then
    image_tag_uid=$3
else
    image_tag_uid=$(cat /proc/sys/kernel/random/uuid | cut -b-8)
fi

ANSIBLE_OPTS="${ANSIBLE_OPTS} -e gpu_operator_git_repo=${git_repo}"
ANSIBLE_OPTS="${ANSIBLE_OPTS} -e gpu_operator_git_ref=${git_ref}"
ANSIBLE_OPTS="${ANSIBLE_OPTS} -e gpu_operator_image_tag_uid=${image_tag_uid}"

ANSIBLE_OPTS="${ANSIBLE_OPTS} -e install_nfd_operator_from_hub=no"
ANSIBLE_OPTS="${ANSIBLE_OPTS} -e undeploy_gpu_operator=no"
ANSIBLE_OPTS="${ANSIBLE_OPTS} -e user_mode=not-ci"

exec ansible-playbook ${ANSIBLE_OPTS} playbooks/deploy-gpu-operator-from-commit.yml
