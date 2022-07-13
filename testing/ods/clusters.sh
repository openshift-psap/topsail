#! /bin/bash

set -o pipefail
set -o errexit
set -o nounset
set -o errtrace
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

    export KUBECONFIG="${SHARED_DIR}/${cluster_role}_kubeconfig"
    if oc get cm/keep-cluster -n default 2>/dev/null; then
        echo "INFO: keep-cluster CM found in the default namespace of the $cluster_type/$cluster_role, keep it."
        return
    fi

    finalize_cluster "$cluster_role"

    "$THIS_DIR/${cluster_type}_cluster.sh" destroy "$cluster_role"
}

create_clusters() {
    cluster_type=$1
    shift || truez
    create_flag="${1:-}"
    shift || true

    if [[ "$cluster_type" == "osd" || "$cluster_type" == "ocp" ]]; then
        process_ctrl::run_in_bg "$THIS_DIR/${cluster_type}_cluster.sh" create "sutest"

        process_ctrl::run_in_bg "$THIS_DIR/ocp_cluster.sh" create "driver"

    elif [[ "$cluster_type" == "single" ]]; then
        process_ctrl::run_in_bg "$THIS_DIR/ocp_cluster.sh" create "sutest"

        echo "INFO: launching a single cluster, creating a symlink for the driver cluster"
        ln -s "${SHARED_DIR}/sutest_kubeconfig" "${SHARED_DIR}/driver_kubeconfig"

    else
        echo "ERROR: invalid cluster type: '$cluster_type'"
        exit 1
    fi

    process_ctrl::wait_bg_processes

    if [[ "$create_flag" == "keep" ]]; then
        KUBECONFIG_DRIVER="${SHARED_DIR}/driver_kubeconfig" # cluster driving the test
        KUBECONFIG_SUTEST="${SHARED_DIR}/sutest_kubeconfig" # system under test

        keep_cluster() {
            cluster_role=$1

            echo "Keeping the $cluster_role cluster ..."
            export PSAP_ODS_SECRET_PATH
            oc create cm keep-cluster -n default --from-literal=keep=true

            bash -ceE '
            source "$PSAP_ODS_SECRET_PATH/create_osd_cluster.password"
            B64_PASS_HASH=$(cd subprojects/kube-password; go run . "$KUBEADMIN_PASS")
            cat << EOF | oc apply -f-
apiVersion: v1
kind: Secret
metadata:
  name: kubeadmin
  namespace: kube-system
type: Opaque
data:
  kubeadmin: "$B64_PASS_HASH"
EOF
'
            oc whoami --show-console > "$ARTIFACT_DIR/${cluster_role}_console.link"
            cat <<EOF > "$ARTIFACT_DIR/${cluster_role}_oc-login.cmd"
source "\$PSAP_ODS_SECRET_PATH/create_osd_cluster.password"
oc login $(oc whoami --show-server) --insecure-skip-tls-verify --username=kubeadmin --password="\$KUBEADMIN_PASS"
EOF
            CLUSTER_TAG=$(oc get machines -n openshift-machine-api -ojsonpath={.items[0].spec.providerSpec.value.tags[0].name} | cut -d/ -f3)
            echo "$OCP_REGION $CLUSTER_TAG" > "$ARTIFACT_DIR/${cluster_role}_cluster_tag"
        }


        KUBECONFIG=$KUBECONFIG_DRIVER keep_cluster driver

        # * 'osd' clusters already have their kubeadmin password
        # populated during the cluster bring up
        # * 'single' clusters already have been modified with the
        # keep_cluster call of the sutest cluster.
        if [[ "$cluster_type" == "ocp" ]]; then
            KUBECONFIG=$KUBECONFIG_SUTEST keep_cluster sutest
        fi
    fi
}

destroy_clusters() {
    cluster_type=$1

    if [[ "$cluster_type" == "osd" || "$cluster_type" == "ocp" ]]; then
        process_ctrl::run_in_bg destroy_cluster "$cluster_type" "sutest"
        process_ctrl::run_in_bg destroy_cluster "ocp" "driver"

    elif [[ "$cluster_type" == "single" ]]; then
        process_ctrl::run_in_bg destroy_cluster "ocp" "sutest"
        echo "INFO: only one cluster was created, nothing to destroy for the driver cluster"
    else
        echo "ERROR: invalid cluster type: '$cluster_type'"
        # don't 'exit 1' in the destroy step,
        # that would prevent the destruction of other clusters
    fi

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

if [[ -z "${action}" || -z "${cluster_type}" ]]; then
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
