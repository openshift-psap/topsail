#! /bin/bash

set -o pipefail
set -o errexit
set -o nounset

create_cluster() {
    echo "Create cluster"
    echo "ODS-Cluster $(date)" > /tmp/ODS_KUBECONFIG
}

destroy_cluster() {
    echo "Destroy cluster"
    cat /tmp/ODS_KUBECONFIG || true
}

# ---

if [ -z "${1:-}" ]; then
    echo "FATAL: $0 expects at least 1 argument ..."
    exit 1
fi

action="$1"
shift

case ${action} in
    "create")
        create_cluster "$@"
        exit 0
        ;;
    "destroy")
        destroy_cluster "@"
        exit 0
        ;;
    *)
        echo "FATAL: Unknown action: ${action}" "$@"
        exit 1
        ;;
esac
