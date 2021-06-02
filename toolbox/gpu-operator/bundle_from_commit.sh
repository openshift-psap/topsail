#! /bin/bash -e

THIS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
source ${THIS_DIR}/../_common.sh

usage() {
   cat <<EOF


Usage:
  $0 [-h|--help]
     Display this message.

  $0 <git repository> <git reference> <quay_push_secret> <quay_image_image> [gpu_operator_image_tag_uid]
     Build an image of the GPU Operator from sources (<git repository> <git reference>)
     and push it to quay.io <quay_image_image> using the <quay_push_secret> credentials.

Example:
 $0 https://github.com/NVIDIA/gpu-operator.git master /path/to/quay_secret.yaml quay.io/org/image_name

See 'oc get imagestreamtags -n gpu-operator-ci -oname' for the tag-uid to reuse.
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
    usage
    exit 0
fi

if [ "$#" -lt 4 ]; then
    echo "FATAL: not enough parameters. Expected at least 4, got $#."

    usage

    exit 1
fi

git_repo=$1
git_ref=$2
quay_push_secret=$3
quay_image_name=$4

if [ "$#" -eq 5 ]; then
    image_tag_uid=$5
else
    image_tag_uid=$(cat /proc/sys/kernel/random/uuid | cut -b-8)
fi

ANSIBLE_OPTS="${ANSIBLE_OPTS} -e gpu_operator_git_repo=${git_repo}"
ANSIBLE_OPTS="${ANSIBLE_OPTS} -e gpu_operator_git_ref=${git_ref}"
ANSIBLE_OPTS="${ANSIBLE_OPTS} -e gpu_operator_image_tag_uid=${image_tag_uid}"

ANSIBLE_OPTS="${ANSIBLE_OPTS} -e gpu_operator_commit_quay_push_secret=${quay_push_secret}"
ANSIBLE_OPTS="${ANSIBLE_OPTS} -e gpu_operator_commit_quay_image_name=${quay_image_name}"


exec ansible-playbook ${ANSIBLE_OPTS} playbooks/gpu_operator_bundle_from_commit.yml
