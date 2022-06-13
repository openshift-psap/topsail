#! /bin/bash

set -o pipefail
set -o errexit
set -o nounset


THIS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
source "$THIS_DIR/common.sh"
source "$THIS_DIR/process_ctrl.sh"
source "$THIS_DIR/../prow/_logging.sh"

# ---

create_clusters() {
    process_ctrl::run_in_bg "$THIS_DIR/ods_cluster.sh" create "$@" &

    process_ctrl::wait_bg_processes
}

destroy_clusters() {
    process_ctrl::run_in_bg "$THIS_DIR/ods_cluster.sh" destroy "$@" &

    process_ctrl::wait_bg_processes
}

# ---

if [ -z "${SHARED_DIR:-}" ]; then
    echo "FATAL: multi-stage test directory \$SHARED_DIR not set ..."
    exit 1
fi

action="${1:-}"
if [ -z "${action}" ]; then
    echo "FATAL: $0 expects at least 1 argument ..."
    exit 1
fi

shift

set -x

finalizers+=("process_ctrl::kill_bg_processes")

case ${action} in
    "create")
        create_clusters "$@"
        exit 0
        ;;
    "destroy")
        destroy_clusters "@"
        exit 0
        ;;
    *)
        echo "FATAL: Unknown action: ${action}" "$@"
        exit 1
        ;;
esac
