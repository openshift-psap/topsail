#! /bin/bash

set -o pipefail
set -o errexit
set -o nounset
set -o errtrace
set -x

TESTING_THIS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
TESTING_UTILS_DIR="$TESTING_THIS_DIR/../utils"

source "$TESTING_THIS_DIR/configure.sh"

clusters_create__check_test_size() {
    echo "Nothing to do yet to check the size of the cluster. All good."
}

export -f clusters_create__check_test_size

exec "$TOPSAIL_DIR/projects/cluster/subprojects/deploy-topsail-clusters/clusters.sh" "$@"
