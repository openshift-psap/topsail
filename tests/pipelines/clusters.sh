#! /bin/bash

set -o pipefail
set -o errexit
set -o nounset
set -o errtrace
set -x

PROJECTS_THIS_TESTING_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
TOPSAIL_DIR="$PROJECTS_THIS_TESTING_DIR/../../.."
TESTING_UTILS_DIR="$TOPSAIL_DIR/testing/utils"

source "$PROJECTS_THIS_TESTING_DIR/configure.sh"

source "$TESTING_THIS_DIR/configure.sh"

clusters_create__check_test_size() {
    echo "Nothing to do yet to check the size of the Pipelines cluster. All good."
}

export -f clusters_create__check_test_size

exec "$TOPSAIL_DIR/projects/cluster/subprojects/deploy-topsail-clusters/clusters.sh" "$@"
