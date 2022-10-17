#! /bin/bash

set -o pipefail
set -o errexit
set -o nounset
set -o errtrace

TESTING_ODS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

source "$TESTING_ODS_DIR/../_logging.sh"
source "$TESTING_ODS_DIR/configure.sh"
source "$TESTING_ODS_DIR/cluster_helpers.sh"

# ---

create_cluster() {
    local cluster_role=$1

    export ARTIFACT_TOOLBOX_NAME_PREFIX="${cluster_role}_osd_"

    local cluster_name="$(get_config clusters.create.name_prefix)"

    if test_config clusters.create.keep; then
        local author=$(echo "$JOB_SPEC" | jq -r .refs.pulls[0].author)
        cluster_name="${author}-$(date %m%d-%Hh%M)"

    elif [[ "${PULL_NUMBER:-}" ]]; then
        cluster_name="${cluster_name}${PULL_NUMBER}-$(date +%Hh%M)"
    else
        cluster_name="${cluster_name}$(date +%y%m%d%H%M)"
    fi

    echo "Create cluster $cluster_name..."
    echo "$cluster_name" > "$CONFIG_DEST_DIR/${cluster_role}_managed_cluster_name"

    KUBECONFIG="$CONFIG_DEST_DIR/${cluster_role}_kubeconfig"
    touch "$KUBECONFIG"

    echo "$cluster_name" > "$ARTIFACT_DIR/${cluster_role}_managed_cluster.name"
    if test_config clusters.sutest.managed.is_ocm; then
        cluster_helpers::ocm_login

        ./run_toolbox.py cluster create_osd \
                         "$cluster_name" \
                         "$PSAP_ODS_SECRET_PATH/create_osd_cluster.password" \
                         "$KUBECONFIG" \
                         --compute_machine_type="$(get_config clusters.create.ocm.workers.type)" \
                         --compute_nodes="$(get_config clusters.create.ocm.workers.count)" \
                         --version="$(get_config clusters.create.ocm.version)" \
                         --region="$(get_config clusters.create.ocm.region)"

        ocm describe cluster "$cluster_name" --json \
            | jq .id -r \
                 > "$ARTIFACT_DIR/${cluster_role}_managed_cluster.id"
    elif test_config clusters.sutest.managed.is_rosa; then
        _error "ROSA cluster creation not supported"
    else
        _error "managed cluster must be ROSA or OCM ..."
    fi
}

destroy_cluster() {
    local cluster_role=$1

    export ARTIFACT_TOOLBOX_NAME_PREFIX="${cluster_role}_osd_"

    local cluster_name="$(cat "$CONFIG_DEST_DIR/${cluster_role}_managed_cluster_name" || true)"
    if [[ -z "$cluster_name" ]]; then
        echo "No managed cluster to destroy ..."
        exit 0
    fi

    if test_config clusters.sutest.managed.is_ocm; then

        cluster_helpers::ocm_login
        ./run_toolbox.py cluster destroy_osd "$cluster_name"
    elif test_config clusters.sutest.managed.is_rosa; then
        _error "cannot destroy ROSA clusters ..."
    else
        _error "managed cluster must be ROSA or OCM ..."
    fi

    echo "Deletion of cluster '$cluster_name' successfully requested."
}

# ---

if [[ -z "${ARTIFACT_DIR:-}" ]]; then
    _error "artifacts storage directory ARTIFACT_DIR not set ..."
fi

if [[ "${CONFIG_DEST_DIR:-}" ]]; then
    echo "Using CONFIG_DEST_DIR=$CONFIG_DEST_DIR ..."

elif [[ "${SHARED_DIR:-}" ]]; then
    echo "Using CONFIG_DEST_DIR=\$SHARED_DIR=$SHARED_DIR ..."
    CONFIG_DEST_DIR=$SHARED_DIR
else
    _error "CONFIG_DEST_DIR or SHARED_DIR must be set ..."
fi

action=${1:-}
cluster_role=${2:-}

set -x

case ${action} in
    "create")
        create_cluster "$cluster_role"
        exit 0
        ;;
    "destroy")
        set +o errexit
        destroy_cluster "$cluster_role"
        exit 0
        ;;
    *)
        _error "Unknown action: ${action} $cluster_role"
        exit 1
        ;;
esac
