#! /usr/bin/env bash

set -o pipefail
set -o errexit
set -o nounset

nto_e2e() {
    toolbox/cluster/capture_environment.sh
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
    -*)
        echo "FATAL: Unknown option: ${action}"
        exit 1
        ;;
    *)
        echo "FATAL: Unknown action \"${action}\""
        exit 1
        ;;
esac
