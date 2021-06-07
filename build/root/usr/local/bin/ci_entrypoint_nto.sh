#! /usr/bin/env bash

set -o pipefail
set -o errexit
set -o nounset

nto_e2e() {
    local commit=${1:-}

    test $commit || {
        commit=origin/release-$(oc get clusterversion -o jsonpath='{.items[].status.desired.version}' | grep -Po '^\d+\.\d+')
    }
    toolbox/nto/test-e2e.sh "$commit"
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
