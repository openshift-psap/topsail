#! /bin/bash

#set -o pipefail
#set -o errexit
#set -o nounset

create_cluster() {
    echo "Create cluster ($SHARED_DIR)"
    echo "ODS-Cluster $(date)" > /$SHARED_DIR/ODS_KUBECONFIG || true
    ls $SHARED_DIR
}

destroy_cluster() {
    echo "Destroy cluster ($SHARED_DIR)"
    cat /$SHARED_DIR/ODS_KUBECONFIG || true
    ls $SHARED_DIR
}

# ---

if [ -z "${1:-}" ]; then
    echo "FATAL: $0 expects at least 1 argument ..."
    exit 1
fi

action="$1"
shift

set -x

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
