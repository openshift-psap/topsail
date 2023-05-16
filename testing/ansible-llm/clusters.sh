#! /bin/bash

set -o pipefail
set -o errexit
set -o nounset
set -o errtrace
set -x

TESTING_PIPELINES_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
TESTING_UTILS_DIR="$TESTING_PIPELINES_DIR/../utils"

source "$TESTING_PIPELINES_DIR/configure.sh"

clusters_create__check_test_size() {
    echo "Nothing to do yet to check the size of the Pipelines cluster. All good."
}

export -f clusters_create__check_test_size

exec "$TESTING_UTILS_DIR/openshift_clusters/clusters.sh" "$@"
