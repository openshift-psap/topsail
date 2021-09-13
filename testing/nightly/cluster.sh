#! /usr/bin/env bash

set -o pipefail
set -o errexit
set -o nounset

THIS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd ${THIS_DIR}/../..

cluster_upgrade() {
    if [ -z "${CLUSTER_UPGRADE_TARGET_IMAGE:-}" ]; then
        echo "FATAL: CLUSTER_UPGRADE_TARGET_IMAGE must be provided to upgrade the cluster"
        exit 1
    fi
    ./run_toolbox.py cluster upgrade_to_image "$CLUSTER_UPGRADE_TARGET_IMAGE"
}

if [ -z "${1:-}" ]; then
    echo "FATAL: $0 expects at least 1 argument ..."
    exit 1
fi

action="${1:-}"
shift

set -x

case ${action} in
    "upgrade")
        cluster_upgrade
        exit 0
        ;;
    *)
        echo "FATAL: Action not supported: '$action')"
        exit 1
        ;;
esac
