#!/bin/bash

set -euxo pipefail

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")

source "${SCRIPT_DIR}"/../config.env

pushd "${SCRIPT_DIR}"

podman build -f Containerfile.sync sync/ -t ${QUAY_REPO}:sync
podman build -f Containerfile.serve serve/ -t ${QUAY_REPO}:serve

echo "Done"
