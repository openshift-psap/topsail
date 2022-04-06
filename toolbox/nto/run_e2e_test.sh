#! /bin/bash -e

THIS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
source ${THIS_DIR}/../_common.sh

nto_git_repo=https://github.com/openshift/cluster-node-tuning-operator.git

usage() {
    cat >&2 <<_USAGE_
Usage:   $0 <git repository> <git reference>
Example: $0 $nto_git_repo master
_USAGE_

  test "${1:-}" && exit $1
}

while true
do
    case "${1:-}" in
        -h|--[Hh][Ee][Ll][Pp])
            usage 0
            ;;
        -*) echo "$0: invalid option '${1:-}'" >&2
            usage 1
            ;;
        *)  break
            ;;
    esac
    shift
done

git_repo=${1:-$nto_git_repo}
git_ref=${2:-}

test "$git_ref" || {
    git_ref=origin/release-$(oc get clusterversion -o jsonpath='{.items[].status.desired.version}' | grep -Po '^\d+\.\d+')
}

exec ./run_toolbox.py nto run_e2e_test "${git_repo}" "${git_ref}"
