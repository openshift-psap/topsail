#!/bin/bash

set -euxo pipefail

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")

source "${SCRIPT_DIR}"/../config.env

pushd "${SCRIPT_DIR}"

podman push $QUAY_REPO:sync
podman push $QUAY_REPO:serve

echo "Done"
