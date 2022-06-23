#! /bin/bash

set -o pipefail
set -o errexit
set -o nounset


THIS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
source "$THIS_DIR/common.sh"
source "$THIS_DIR/process_ctrl.sh"
source "$THIS_DIR/../prow/_logging.sh"

# ---

prepare_deploy_cluster_subproject() {
    cd subprojects/deploy-cluster/

    mkdir "${HOME}/.aws"
    cp "${PSAP_ODS_SECRET_PATH}/.awscred" "${HOME}/.aws/credentials"

    cp utils/config.mk{.sample,}
    cp utils/install-config.yaml{.sample,}
}

create_ocp_cluster() {
    cluster=$1

    # ---

    prepare_deploy_cluster_subproject

    cluster_name="${CLUSTER_NAME_PREFIX}"
    if [[ "${PULL_NUMBER:-}" ]]; then
        cluster_name="${cluster_name}-pr${PULL_NUMBER}-${BUILD_ID}"
    else
        cluster_name="${cluster_name}-$(date +%Y%m%d-%Hh%M)"
    fi

    yq -yi '.compute[0].replicas='$OCP_WORKER_NODES utils/install-config.yaml
    yq -yi '.compute[0].platform.aws.type = "'$OCP_WORKER_MACHINE_TYPE'"' utils/install-config.yaml
    yq -yi '.controlPlane.platform.aws.type = "'$OCP_MASTER_MACHINE_TYPE'"' utils/install-config.yaml
    yq -yi '.platform.aws.region="'$OCP_REGION'"' utils/install-config.yaml

    export PSAP_ODS_SECRET_PATH

    bash -ce 'sed "s|<PULL-SECRET>|'\''$(cat "$PSAP_ODS_SECRET_PATH/pull-secret")'\''|" -i utils/install-config.yaml'
    bash -ce 'sed "s|<SSH-KEY>|$(cat "$PSAP_ODS_SECRET_PATH/ssh-publickey")|" -i utils/install-config.yaml'

    install_dir="/tmp/${cluster}_installer"
    mkdir "$install_dir"
    make cluster \
         OCP_VERSION="${OCP_VERSION}" \
         CLUSTER_PATH="${install_dir}" \
         CLUSTER_NAME="${cluster_name}" \
         DIFF_TOOL= \
        | grep --line-buffered -v 'password\|X-Auth-Token\|UserData:' > "${ARTIFACT_DIR}/${cluster}_install.log"

    cp "${install_dir}/auth/kubeadmin-password" \
       "${SHARED_DIR}/${cluster}_kubeadmin-password"

    cp "${install_dir}/metadata.json" \
       "${SHARED_DIR}/${cluster}_metadata.json"

    cp "${install_dir}/auth/kubeconfig" \
        "${SHARED_DIR}/${cluster}_kubeconfig"

    # ---

    yq -yi  'del(.pullSecret)' "${install_dir}/install-config.back.yaml"
    yq -yi  'del(.sshKey)' "${install_dir}/install-config.back.yaml"

    cp "${install_dir}/install-config.back.yaml" \
        "${ARTIFACT_DIR}/${cluster}_install-config.yaml"
}

delete_rhods_postgres() {
    cluster=$1
    export KUBECONFIG="$SHARED_DIR/${cluster}_kubeconfig"

    # Destroy Postgres database to avoid AWS leaks ...
    # See https://issues.redhat.com/browse/MGDAPI-4118

    if ! oc get postgres/jupyterhub-db-rds -n redhat-ods-applications 2>/dev/null; then
        echo "INFO: No Postgres database available in the $cluster cluster, nothing to delete."
        return
    fi

    if ! oc delete postgres/jupyterhub-db-rds -n redhat-ods-applications; then
        echo "WARNING: Postgres database could not be deleted in the ..."
    fi
}

capture_gather_extra() {
    cluster=$1

    base_artifact_dir=$ARTIFACT_DIR

    export ARTIFACT_DIR=$base_artifact_dir/${cluster}__gather-extra
    export KUBECONFIG=$SHARED_DIR/${cluster}_kubeconfig

    "$THIS_DIR"/../gather-extra.sh > "$base_artifact_dir/${cluster}__gather-extra.log" 2>&1 || true

    export ARTIFACT_DIR=$base_artifact_dir
}

finalize_cluster() {
    cluster=$1

    capture_gather_extra "$cluster"

    delete_rhods_postgres "$cluster"
}

destroy_ocp_cluster() {
    cluster=$1

    finalize_cluster "$cluster"

    prepare_deploy_cluster_subproject

    destroy_dir="/tmp/${cluster}_destroy"
    mkdir "$destroy_dir"

    cp "${SHARED_DIR}/${cluster}_metadata.json" "${destroy_dir}/metadata.json"

    make uninstall \
         OCP_VERSION="${OCP_VERSION}" \
         CLUSTER_PATH="${destroy_dir}" \
         > "${ARTIFACT_DIR}/${cluster}_destroy.log" \
         2>&1
}

destroy_osd_cluster() {
    cluster=$1

    finalize_cluster "$cluster"

    "$THIS_DIR/osd_cluster.sh" destroy "$@"
}

create_clusters() {
    process_ctrl::run_in_bg create_ocp_cluster "driver"
    process_ctrl::run_in_bg "$THIS_DIR/osd_cluster.sh" create "sutest"

    process_ctrl::wait_bg_processes
}

destroy_clusters() {
    process_ctrl::run_in_bg destroy_ocp_cluster "driver"
    process_ctrl::run_in_bg destroy_osd_cluster "sutest"

    process_ctrl::wait_bg_processes
}

# ---

if [ -z "${SHARED_DIR:-}" ]; then
    echo "FATAL: multi-stage test directory \$SHARED_DIR not set ..."
    exit 1
fi

action="${1:-}"
mode="${2:-}"
if [[ -z "${action}" || -z "${action}" ]]; then
    echo "FATAL: $0 expects 2 arguments (action mode) ..."
    exit 1
fi

shift
shift
exit 0 #

set -x

case ${action} in
    "create")
        finalizers+=("process_ctrl::kill_bg_processes")
        create_clusters "$mode" "$@"
        exit 0
        ;;
    "destroy")
        set +o errexit
        destroy_clusters "$mode" "$@"
        exit 0
        ;;
    *)
        echo "FATAL: Unknown action: $action $mode" "$@"
        exit 1
        ;;
esac
