#! /bin/bash

set -o pipefail
set -o errexit
set -o nounset
set -o errtrace

THIS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
source "$THIS_DIR/config_common.sh"
source "$THIS_DIR/config_clusters.sh"
source "$THIS_DIR/cluster_helpers.sh"

# ---

create_cluster() {
    cluster_role=$1
    create_flag=$2

    export ARTIFACT_TOOLBOX_NAME_PREFIX="${cluster_role}_osd_"

    cluster_name="${CLUSTER_NAME_PREFIX}"

    if [[ "$create_flag" == "keep" ]]; then
        author=$(echo "$JOB_SPEC" | jq -r .refs.pulls[0].author)
        cluster_name="${author}-$(date %m%d-%Hh%M)"

    elif [[ "${PULL_NUMBER:-}" ]]; then
        cluster_name="${cluster_name}${PULL_NUMBER}-$(date +%Hh%M)"
    else
        cluster_name="${cluster_name}$(date +%y%m%d%H%M)"
    fi

    echo "Create cluster $cluster_name..."
    echo "$cluster_name" > "$SHARED_DIR/${cluster_role}_osd_cluster_name"

    KUBECONFIG="$SHARED_DIR/${cluster_role}_kubeconfig"
    touch "$KUBECONFIG"

    cluster_helpers::ocm_login

    echo "$cluster_name" > "$ARTIFACT_DIR/${cluster_role}_osd_cluster.name"
    ./run_toolbox.py cluster create_osd \
                     "$cluster_name" \
                     "$PSAP_ODS_SECRET_PATH/create_osd_cluster.password" \
                     "$KUBECONFIG" \
                     --compute_machine_type="$OSD_WORKER_NODES_TYPE" \
                     --compute_nodes="$OSD_WORKER_NODES_COUNT" \
                     --version="$OSD_VERSION" \
                     --region="$OSD_REGION"

    ocm describe cluster "$cluster_name" --json | jq .id -r > "$ARTIFACT_DIR/${cluster_role}_osd_cluster.id"
}

destroy_cluster() {
    cluster_role=$1

    export ARTIFACT_TOOLBOX_NAME_PREFIX="${cluster_role}_osd_"

    cluster_name=$(get_osd_cluster_name "$cluster_role")
    if [[ -z "$cluster_name" ]]; then
        echo "No OSD cluster to destroy ..."
        exit 0
    fi

    cluster_helpers::ocm_login
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
    echo "FATAL: $0 expects 2 arguments: (create|destoy) CLUSTER_ROLE"
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
        set +o errexit
        destroy_cluster "$@"
        exit 0
        ;;
    *)
        echo "FATAL: Unknown action: ${action}" "$@"
        exit 1
        ;;
esac
