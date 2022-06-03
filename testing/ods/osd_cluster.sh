#! /bin/bash

set -o pipefail
set -o errexit
set -o nounset


THIS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
source "$THIS_DIR/common.sh"

# ---

create_cluster() {
    CLUSTER_NAME="${CLUSTER_NAME_PREFIX}$(date +%y%m%d%H%M)"
    echo "Create cluster $CLUSTER_NAME..."
    echo "$CLUSTER_NAME" > "$SHARED_DIR/osd_cluster_name"

    touch "$SHARED_DIR/kubeconfig"

    ocm_login
    ./run_toolbox.py cluster create_osd \
                     "$CLUSTER_NAME" \
                     "$PSAP_ODS_SECRET_PATH/create_osd_cluster.password" \
                     "$SHARED_DIR/kubeconfig" \
                     --compute_machine_type="$OSD_COMPUTE_MACHINE_TYPE" \
                     --compute_nodes="$OSD_COMPUTE_NODES" \
                     --version="$OSD_VERSION" \
                     --region="$OSD_REGION"
}

destroy_cluster() {
    cluster_name=$(get_osd_cluster_name)
    if [[ -z "$cluster_name" ]]; then
        echo "No OSD cluster to destroy ..."
        exit 0
    fi

    ocm_login
    ./run_toolbox.py cluster destroy_osd "$cluster_name"

    echo "Deletion of cluster '$cluster_name' successfully requested."
}

# ---

if [ -z "${SHARED_DIR:-}" ]; then
    echo "FATAL: multi-stage test \$SHARED_DIR not set ..."
    exit 1
fi

action="${1:-}"
if [ -z "${action}" ]; then
    echo "FATAL: $0 expects at least 1 argument ..."
    exit 1
fi


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
