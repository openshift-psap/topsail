#! /usr/bin/env bash

set -o pipefail
set -o errexit
set -o nounset

cluster_upgrade() {
    if [ -z "${CLUSTER_UPGRADE_TARGET_IMAGE:-}" ]; then
        echo "FATAL: CLUSTER_UPGRADE_TARGET_IMAGE must be provided to upgrade the cluster"
        exit 1
    fi
    toolbox/cluster/upgrade_to_image.sh "$CLUSTER_UPGRADE_TARGET_IMAGE"
}

if [ -z "${1:-}" ]; then
    echo "FATAL: $0 expects at least 1 argument ..."
    exit 1
fi

action="${1:-}"
shift

set -x

case ${action:-} in
    "upgrade")
        cluster_upgrade
        exit 0
    -*)
        echo "FATAL: Unknown option: ${action}"
        exit 1
        ;;
    *)
        echo "FATAL: Nothing to do ..."
        exit 1
        ;;
esac
