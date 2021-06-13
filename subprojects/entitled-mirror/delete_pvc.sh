#!/bin/bash

set -euxo pipefail

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")

source ${SCRIPT_DIR}/config.env

oc delete -n ${NAMESPACE} pvc/${NAME}
