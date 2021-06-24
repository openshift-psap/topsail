#!/bin/bash

set -euxo pipefail

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")

ENTITLEMENT_FILE=${SCRIPT_DIR}/entitlement.pem

if [[ ! -f "${ENTITLEMENT_FILE}" ]]; then
    echo "Please place your entitlement PEM file in ${ENTITLEMENT_FILE} before running this script"
    exit 1
fi

if ! command -v podman-compose &> /dev/null; then
    echo "Please install podmanc-compose before running this script"
    exit 1
fi

podman-compose down
podman-compose up

