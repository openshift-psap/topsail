#! /bin/bash

set -o pipefail
set -o errexit
set -o nounset
set -o errtrace

THIS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
source "$THIS_DIR/common.sh"

# ---

create_cluster() {
    cluster_role=$1

    export ARTIFACT_TOOLBOX_NAME_PREFIX="osd_${cluster_role}_"

    cluster_name="${CLUSTER_NAME_PREFIX}"

    if [[ "${JOB_NAME_SAFE:-}" == "$JOB_NAME_SAFE_GET_CLUSTER" ]]; then
        author=$(echo "$JOB_SPEC" | jq -r .refs.pulls[0].author)
        cluster_name="${author}-$(date %m%d-%Hh%M)"

    elif [[ "${PULL_NUMBER:-}" ]]; then
        cluster_name="${cluster_name}${PULL_NUMBER}-$(date +%Hh%M)"
    else
        cluster_name="${cluster_name}$(date +%y%m%d%H%M)"
    fi

    echo "Create cluster $cluster_name..."
    echo "$cluster_name" > "$SHARED_DIR/osd_${cluster_role}_cluster_name"

    KUBECONFIG="$SHARED_DIR/${cluster_role}_kubeconfig"
    touch "$KUBECONFIG"

    ocm_login

    compute_nodes_type=$(get_compute_node_type "$cluster_role" osd)
    compute_nodes_count=$(get_compute_node_count "$cluster_role" osd "$compute_nodes_type")

    echo "$cluster_name" > "$ARTIFACT_DIR/${cluster_role}_osd_cluster.name"
    ./run_toolbox.py cluster create_osd \
                     "$cluster_name" \
                     "$PSAP_ODS_SECRET_PATH/create_osd_cluster.password" \
                     "$KUBECONFIG" \
                     --compute_machine_type="$compute_nodes_type" \
                     --compute_nodes="$compute_nodes_count" \
                     --version="$OSD_VERSION" \
                     --region="$OSD_REGION"
    ocm describe cluster "$cluster_name" --json | jq .id -r > "$ARTIFACT_DIR/${cluster_role}_osd_cluster.id"

    if [[ "$cluster_role" == "sutest" && "$ENABLE_AUTOSCALER" ]]; then
        MACHINEPOOL_NAME=default

        ocm edit machinepool "$MACHINEPOOL_NAME" --cluster "$cluster_name" \
            --enable-autoscaling --min-replicas=2 --max-replicas=150
    fi
}

destroy_cluster() {
    cluster_role=$1

    export ARTIFACT_TOOLBOX_NAME_PREFIX="osd_${cluster_role}_"

    cluster_name=$(get_osd_cluster_name "$cluster_role")
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
