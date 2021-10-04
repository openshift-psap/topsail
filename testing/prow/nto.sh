#! /usr/bin/env bash

set -o pipefail
set -o errexit
set -o nounset

THIS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd ${THIS_DIR}/../..

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
        nto_e2e "$@"
        exit 0
        ;;
    *)
        echo "FATAL: Unknown action \"${action}\""
        exit 1
        ;;
esac
