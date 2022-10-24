#! /bin/bash

set -o pipefail
set -o errexit
set -o nounset
set -o errtrace
set -x

THIS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

source "$THIS_DIR/config_common.sh"
source "$THIS_DIR/config_clusters.sh"
source "$THIS_DIR/cluster_helpers.sh"

# ---

export AWS_SHARED_CREDENTIALS_FILE="${PSAP_ODS_SECRET_PATH:-}/.awscred"

prepare_deploy_cluster_subproject() {
    cd subprojects/deploy-cluster/

    cp utils/config.mk{.sample,}
    cp utils/install-config.yaml{.sample,}

    local DOWNLOAD_OCP_INSTALLER_FROM_PRIVATE=
    if [[ "$DOWNLOAD_OCP_INSTALLER_FROM_PRIVATE" ]]; then
        mkdir -p "/opt/ci-artifacts/src/subprojects/deploy-cluster/utils/installers/$ocp_version"
        wget --quiet "https://people.redhat.com/~kpouget/22-10-05/openshift-install-linux-$ocp_version.tar.gz"
        tar xzf "openshift-install-linux-$ocp_version.tar.gz" openshift-install
        mv openshift-install "/opt/ci-artifacts/src/subprojects/deploy-cluster/utils/installers/$ocp_version/openshift-install"
        rm "openshift-install-linux-$ocp_version.tar.gz"
    fi

    make has_installer OCP_VERSION="${OCP_VERSION}"

    if [[ ! -f ${AWS_SHARED_CREDENTIALS_FILE} ]]; then
        echo "ERROR: AWS credentials file not found in the vault ..."
        false
    fi
}

create_cluster() {
    cluster_role=$1
    create_flag=$2

    export ARTIFACT_TOOLBOX_NAME_PREFIX="${cluster_role}_ocp_"
    export AWS_DEFAULT_PROFILE=${AWS_DEFAULT_PROFILE:-ci-artifact}
    # ---

    cd subprojects/deploy-cluster/

    cluster_name="${CLUSTER_NAME_PREFIX}"
    if [[ "$create_flag" == "keep" ]]; then
        author=$(echo "$JOB_SPEC" | jq -r .refs.pulls[0].author)
        cluster_name="${author}-${cluster_role}-$(date +%Y%m%d-%Hh%M)"

        export AWS_DEFAULT_PROFILE="${author}_ci-artifact"
    elif [[ "${PULL_NUMBER:-}" ]]; then
        cluster_name="${cluster_name}-pr${PULL_NUMBER}-${cluster_role}-${BUILD_ID}"
    else
        cluster_name="${cluster_name}-${cluster_role}-$(date +%Hh%M)"
    fi

    export AWS_PROFILE=$AWS_DEFAULT_PROFILE
    echo "Using AWS_[DEFAULT_]PROFILE=$AWS_DEFAULT_PROFILE"

    install_dir="/tmp/${cluster_role}_ocp_installer"
    rm -rf "$install_dir"
    mkdir -p "$install_dir"

    install_dir_config="${install_dir}/install-config.yaml"

    cat utils/install-config.yaml | \
        yq -y '.metadata.name = "'$cluster_name'"' | \
        yq -y '.baseDomain = "'$OCP_BASE_DOMAIN'"' | \
        yq -y '.compute[0].platform.aws.type = "'$OCP_INFRA_MACHINE_TYPE'"' | \
        yq -y '.compute[0].replicas = '$OCP_INFRA_NODES_COUNT | \
        yq -y '.controlPlane.platform.aws.type = "'$OCP_MASTER_MACHINE_TYPE'"' | \
        yq -y '.platform.aws.region = "'$OCP_REGION'"' \
           > "$install_dir_config"

    export PSAP_ODS_SECRET_PATH

    # ensure that the files exist in the vault
    test -f "$PSAP_ODS_SECRET_PATH/pull-secret"
    test -f "$PSAP_ODS_SECRET_PATH/ssh-publickey"

    bash -ce 'sed "s|<PULL-SECRET>|'\''$(cat "$PSAP_ODS_SECRET_PATH/pull-secret")'\''|" -i "'$install_dir_config'"'
    bash -ce 'sed "s|<SSH-KEY>|$(cat "$PSAP_ODS_SECRET_PATH/ssh-publickey")|" -i "'$install_dir_config'"'

    save_install_artifacts() {
        status=$1

        install_config="${install_dir}/install-config.back.yaml"
        if [[ -f "$install_config" ]]; then
            yq -yi 'del(.pullSecret)' "$install_config"
            yq -yi 'del(.sshKey)' "$install_config"

            cp "$install_config" "${ARTIFACT_DIR}/${cluster_role}_ocp_install-config.yaml"
        fi

        [[ "$status" != "success" ]] && exit 1

        return 0
    }

    # ensure that the cluster's 'metadata.json' is copied to the SHARED_DIR even in case of errors
    trap "save_install_artifacts error" ERR SIGTERM SIGINT

    make cluster \
         OCP_VERSION="${OCP_VERSION}" \
         CLUSTER_PATH="${install_dir}" \
         CLUSTER_NAME="${cluster_name}" \
         METADATA_JSON_DEST="${SHARED_DIR}/${cluster_role}_ocp_metadata.json" \
         DIFF_TOOL= \
        | grep --line-buffered -v 'password\|X-Auth-Token\|UserData:' > "${ARTIFACT_DIR}/${cluster_role}_ocp_install.log"

    cp "${install_dir}/auth/kubeadmin-password" \
       "${SHARED_DIR}/${cluster_role}_kubeadmin-password"

    export KUBECONFIG="${SHARED_DIR}/${cluster_role}_kubeconfig"

    cp "${install_dir}/auth/kubeconfig" \
       "$KUBECONFIG"

    cd "$HOME"

    save_install_artifacts success
}


destroy_cluster() {
    cluster_role=$1

    export ARTIFACT_TOOLBOX_NAME_PREFIX="${cluster_role}_ocp_"

    destroy_dir="/tmp/${cluster_role}_ocp_destroy"
    mkdir "$destroy_dir"

    cp "${SHARED_DIR}/${cluster_role}_ocp_metadata.json" "${destroy_dir}/metadata.json"

    cd subprojects/deploy-cluster/

    export AWS_PROFILE=${AWS_PROFILE:-ci-artifact}
    export AWS_DEFAULT_PROFILE=${AWS_DEFAULT_PROFILE:-ci-artifact}

    make uninstall \
         OCP_VERSION="${OCP_VERSION}" \
         CLUSTER_PATH="${destroy_dir}" \
         >"${ARTIFACT_DIR}/${cluster_role}_ocp_destroy.log" \
         2>&1
}

if [[ -z "${SHARED_DIR:-}" ]]; then
    echo "FATAL: multi-stage test directory SHARED_DIR not set ..."
    exit 1
fi

if [[ -z "${ARTIFACT_DIR:-}" ]]; then
    echo "FATAL: artifacts storage directory ARTIFACT_DIR not set ..."
    exit 1
fi

action="${1:-}"
if [[ -z "${action}" ]]; then
    echo "FATAL: $0 expects 2 arguments: (create|destoy) CLUSTER_ROLE"
    exit 1
fi

shift

set -x

case ${action} in
    "prepare")
        prepare_deploy_cluster_subproject "$@"
        exit 0
        ;;
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
