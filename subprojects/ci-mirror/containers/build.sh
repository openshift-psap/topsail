#!/bin/bash

set -euo pipefail

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")

if [[ ${NAMESPACE:-} == "" ]]; then
    echo Please source a mirror configuration file before running this script
    exit 1
fi

set -x

pushd "${SCRIPT_DIR}"

podman build -f Containerfile.sync sync/ -t ${QUAY_REPO}:sync
podman build -f Containerfile.serve serve/ -t ${QUAY_REPO}:serve

echo "Done"
