#! /bin/bash -e

THIS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

RHEL_FLAG="--rhel-beta"

usage() {
    echo "Usage: $0 <repo file abs path> [destinationDir]"
    echo "Usage: $0 ${RHEL_FLAG}"
}

REPOFILE_USE_RHEL="false"
REPOFILE_FILENAME=""
REPOFILE_DESTDIR=""

if [ "$#" -gt 2 ]; then
    echo "FATAL: expected 1 or 2 parameters ... (got $#: '$@')"
    usage
    exit 1
elif [[ "$1" == "${RHEL_FLAG}" ]]; then
    if [ "$#" -gt 1 ]; then
        echo "FATAL: Flag $RHEL_FLAG doesn't take any parameter"
        usage
        exit 1
    fi
    REPOFILE_USE_RHEL="true"
    REPOFILE_DESTDIR="/etc/yum.repos.d"
elif [[ "$1" == "--"* && "$1" != "${RHEL_FLAG}" ]]; then
    echo "FATAL: only ${RHEL_FLAG} flag is allowed"
    usage
    exit 1
elif [[ ! -e "$1" ]]; then
    echo "FATAL: File '$1' not found"
    usage
    exit 1
else
    REPOFILE_FILENAME=$(realpath $1)

    if [[ "{2:-}" ]]; then
        REPOFILE_DESTDIR="${2}"
    fi
fi

source ${THIS_DIR}/../_common.sh

ANSIBLE_OPTS="${ANSIBLE_OPTS} -e gpu_operator_set_repo_filename=${REPOFILE_FILENAME}"
ANSIBLE_OPTS="${ANSIBLE_OPTS} -e gpu_operator_set_repo_use_rhel_beta=${REPOFILE_USE_RHEL}"
if [[ "$REPOFILE_DESTDIR" ]]; then
    ANSIBLE_OPTS="${ANSIBLE_OPTS} -e gpu_operator_set_repo_destdir=${REPOFILE_DESTDIR}"
fi

exec ansible-playbook ${ANSIBLE_OPTS} playbooks/gpu_operator_set_repo-config.yml
