#! /bin/bash -e

THIS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
source ${THIS_DIR}/../_common.sh

nto_e2e() {
    local nto_dir=cluster-node-tuning-operator
    local nto_repo=https://github.com/openshift/$nto_dir
    local commit=${1:-master}

    rm -rf $nto_dir
    git clone -n $nto_repo && cd $nto_dir && git checkout ${commit}
    make test-e2e
    cd ..
}

nto_e2e "$@"
