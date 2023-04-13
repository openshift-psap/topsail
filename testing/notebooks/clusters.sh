#! /bin/bash

set -o pipefail
set -o errexit
set -o nounset
set -o errtrace
set -x

TESTING_NOTEBOOKS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
TESTING_UTILS_DIR="$TESTING_NOTEBOOKS_DIR/../utils"

source "$TESTING_NOTEBOOKS_DIR/configure.sh"

exec "$TESTING_UTILS_DIR/openshift_clusters/clusters.sh" "$@"
