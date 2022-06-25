#! /bin/bash

set -o pipefail
set -o errexit
set -o nounset
set -x

THIS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
source "$THIS_DIR/common.sh"
source "$THIS_DIR/process_ctrl.sh"
source "$THIS_DIR/../prow/_logging.sh"

# ---

delete_rhods_postgres() {
    cluster_role=$1
    export KUBECONFIG="$SHARED_DIR/${cluster_role}_kubeconfig"

    # Destroy Postgres database to avoid AWS leaks ...
    # See https://issues.redhat.com/browse/MGDAPI-4118

    if ! oc get postgres/jupyterhub-db-rds -n redhat-ods-applications 2>/dev/null; then
        echo "INFO: No Postgres database available in the $cluster_role cluster, nothing to delete."
        return
    fi

    if ! oc delete postgres/jupyterhub-db-rds -n redhat-ods-applications; then
        echo "WARNING: Postgres database could not be deleted in the ..."
    fi
}

capture_gather_extra() {
    cluster_role=$1

    base_artifact_dir=$ARTIFACT_DIR

    export ARTIFACT_DIR=$base_artifact_dir/${cluster_role}__gather-extra
    export KUBECONFIG=$SHARED_DIR/${cluster_role}_kubeconfig

    "$THIS_DIR"/../gather-extra.sh > "$base_artifact_dir/${cluster_role}__gather-extra.log" 2>&1 || true

    export ARTIFACT_DIR=$base_artifact_dir
}

finalize_cluster() {
    cluster_role=$1

    delete_rhods_postgres "$cluster_role" & # Delete the postgres database while gathering the extra data

    capture_gather_extra "$cluster_role"

    wait
}

destroy_cluster() {
    cluster_type=$1
    cluster_role=$2

    finalize_cluster "$cluster_role"

    "$THIS_DIR/${cluster_type}_cluster.sh" destroy "$cluster_role"
}

create_clusters() {
    cluster_type=$1

    if [[ "$cluster_type" == "osd" || "$cluster_type" == "ocp" ]]; then
        process_ctrl::run_in_bg "$THIS_DIR/${cluster_type}_cluster.sh" create "sutest"

    elif [[ "$cluster_type" == "single" ]]; then
        echo "INFO: launching a single cluster, creating a symlink for the sutest cluster"
        ln -s "${SHARED_DIR}/driver_kubeconfig" "${SHARED_DIR}/sutest_kubeconfig"

    else
        echo "ERROR: invalid cluster type: '$cluster_type'"
        exit 1
    fi

    process_ctrl::run_in_bg "$THIS_DIR/ocp_cluster.sh" create "driver"

    process_ctrl::wait_bg_processes
}

destroy_clusters() {
    cluster_type=$1

    if [[ "$cluster_type" == "osd" || "$cluster_type" == "ocp" ]]; then
        process_ctrl::run_in_bg destroy_cluster "$cluster_type" "sutest"

    elif [[ "$cluster_type" == "single" ]]; then
        echo "INFO: only one cluster was created, nothing to destroy for the sutest cluster"

    else
        echo "ERROR: invalid cluster type: '$cluster_type'"
        # don't 'exit 1' in the destroy step,
        # that would prevent the destruction of the driver cluster
    fi

    process_ctrl::run_in_bg destroy_cluster "ocp" "driver"

    process_ctrl::wait_bg_processes
}

# ---

if [ -z "${SHARED_DIR:-}" ]; then
    echo "FATAL: multi-stage test storage directory \$SHARED_DIR not set ..."
    exit 1
fi

action="${1:-}"
shift || true
cluster_type="${1:-}"
shift || true

if [[ -z "${action}" || -z "${action}" ]]; then
    echo "FATAL: $0 expects 2 arguments: (create|destroy) (ocp|osd|single)"
    exit 1
fi

set -x

case ${action} in
    "create")
        finalizers+=("process_ctrl::kill_bg_processes")
        "$THIS_DIR/ocp_cluster.sh" prepare

        create_clusters "$cluster_type" "$@"
        exit 0
        ;;
    "destroy")
        set +o errexit
        "$THIS_DIR/ocp_cluster.sh" prepare

        destroy_clusters "$cluster_type" "$@"
        exit 0
        ;;
    *)
        echo "FATAL: Unknown action: $action $cluster_type" "$@"
        exit 1
        ;;
esac
