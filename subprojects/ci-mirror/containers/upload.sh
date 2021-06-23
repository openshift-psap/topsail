#!/bin/bash

set -euo pipefail

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")

if [[ ${NAMESPACE:-} == "" ]]; then
    echo Please source a mirror configuration file before running this script
    exit 1
fi

set -x

pushd "${SCRIPT_DIR}"

podman push ${QUAY_REPO}:sync
podman push ${QUAY_REPO}:serve

echo "Done"
