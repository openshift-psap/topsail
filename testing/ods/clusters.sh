#! /bin/bash

set -o pipefail
set -o errexit
set -o nounset
set -o errtrace
set -x

THIS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

source "$THIS_DIR/process_ctrl.sh"
source "$THIS_DIR/../_logging.sh"
source "$THIS_DIR/config_common.sh"
source "$THIS_DIR/config_clusters.sh"
source "$THIS_DIR/config_load_overrides.sh"

source "$THIS_DIR/cluster_helpers.sh"

# ---

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

    # cluster that will be available right away when going to the debug tab of the test pod
    ln -s "${SHARED_DIR}/${CI_DEFAULT_CLUSTER}_kubeconfig" "${SHARED_DIR}/kubeconfig"

    if [[ "$create_flag" == "keep" ]]; then
        KUBECONFIG_DRIVER="${SHARED_DIR}/driver_kubeconfig" # cluster driving the test
        KUBECONFIG_SUTEST="${SHARED_DIR}/sutest_kubeconfig" # system under test

        keep_cluster() {
            cluster_role=$1

            echo "Keeping the $cluster_role cluster ..."
            export PSAP_ODS_SECRET_PATH
            oc create cm keep-cluster -n default --from-literal=keep=true

            pr_author=$(echo "$JOB_SPEC" | jq -r .refs.pulls[0].author)
            ./run_toolbox.py cluster create_htpasswd_adminuser "$pr_author" "$PSAP_ODS_SECRET_PATH/get_cluster.password"

            oc whoami --show-console > "$ARTIFACT_DIR/${cluster_role}_console.link"
            cat <<EOF > "$ARTIFACT_DIR/${cluster_role}_oc-login.cmd"
source "\$PSAP_ODS_SECRET_PATH/get_cluster.password"
oc login $(oc whoami --show-server) --insecure-skip-tls-verify --username=$pr_author --password="\$password"
EOF
            CLUSTER_TAG=$(oc get machines -n openshift-machine-api -ojsonpath={.items[0].spec.providerSpec.value.tags[0].name} | cut -d/ -f3)
            echo "$CLUSTER_TAG" > "$ARTIFACT_DIR/${cluster_role}_cluster_tag"
            cat <<EOF > "$ARTIFACT_DIR/${cluster_role}_destroy_cluster.cmd"
./run_toolbox.py cluster destroy_ocp $OCP_REGION $CLUSTER_TAG
EOF
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
shift

cluster_type="${CI_DEFAULT_CLUSTER_TYPE:-$PR_POSITIONAL_ARGS}"

if [[ -z "cluster_type" ]]; then
    echo "ERROR: cluster type not found in ODS_CLUSTER_TYPE or PR_POSITIONAL_ARGS"
    exit 1
fi

create_flag=""

if [[ "$cluster_type" == "customer" ]]; then
    cluster_type="single"
elif [[ "$cluster_type" == "get-cluster" ]]; then
    cluster_type="single"
    create_flag="keep"
fi

set -x
case ${action} in
    "create")
        finalizers+=("process_ctrl::kill_bg_processes")
        "$THIS_DIR/ocp_cluster.sh" prepare

        create_clusters "$cluster_type" "$create_flag"
        exit 0
        ;;
    "destroy")
        set +o errexit
        "$THIS_DIR/ocp_cluster.sh" prepare

        destroy_clusters "$cluster_type"
        exit 0
        ;;
    *)
        echo "FATAL: Unknown action: $action $cluster_type" "$@"
        exit 1
        ;;
esac
