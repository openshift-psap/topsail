#! /usr/bin/env bash

set -o pipefail
set -o errexit
set -o nounset

THIS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd ${THIS_DIR}/../..

setup_golang() {
    local version=${1:-1.17.6}
    local bin_dir=${HOME}/bin

    mkdir -p $bin_dir
    curl -sL -o $bin_dir/gimme https://raw.githubusercontent.com/travis-ci/gimme/master/gimme
    chmod +x $bin_dir/gimme

    eval $($bin_dir/gimme $version)
}

nto_e2e() {
    ./run_toolbox.py cluster capture_environment
    toolbox/nto/run_e2e_test.sh "$@"
}

if [ -z "${1:-}" ]; then
    echo "FATAL: $0 expects at least 1 argument ..."
    exit 1
fi

action="${1:-}"
shift

set -x

case ${action:-} in
    "e2e")
        setup_golang
        nto_e2e "$@"
        exit 0
        ;;
    *)
        echo "FATAL: Unknown action \"${action}\""
        exit 1
        ;;
esac
