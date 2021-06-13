#!/bin/bash

set -uxo pipefail

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")

cd ${SCRIPT_DIR}
containers/build.sh && containers/upload.sh && ./delete.sh ; ./deploy.sh
