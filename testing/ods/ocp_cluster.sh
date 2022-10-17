#! /bin/bash

set -o pipefail
set -o errexit
set -o nounset
set -o errtrace
set -x

TESTING_ODS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

source "$TESTING_ODS_DIR/../_logging.sh"
source "$TESTING_ODS_DIR/configure.sh"
source "$TESTING_ODS_DIR/cluster_helpers.sh"

# ---

export AWS_SHARED_CREDENTIALS_FILE="${PSAP_ODS_SECRET_PATH:-}/.awscred"

prepare_deploy_cluster_subproject() {
    cp subprojects/deploy-cluster/utils/config.mk{.sample,}
    cp subprojects/deploy-cluster/utils/install-config.yaml{.sample,}

    local ocp_version=$(get_config clusters.create.ocp.version)

    local DOWNLOAD_OCP_INSTALLER_FROM_PRIVATE=
    if [[ "$DOWNLOAD_OCP_INSTALLER_FROM_PRIVATE" ]]; then
        mkdir -p "/opt/ci-artifacts/src/subprojects/deploy-cluster/utils/installers/$ocp_version"
        wget --quiet "https://people.redhat.com/~kpouget/22-10-05/openshift-install-linux-$ocp_version.tar.gz"
        tar xzf "openshift-install-linux-$ocp_version.tar.gz" openshift-install
        mv openshift-install "/opt/ci-artifacts/src/subprojects/deploy-cluster/utils/installers/$ocp_version/openshift-install"
        rm "openshift-install-linux-$ocp_version.tar.gz"
    fi

    (cd subprojects/deploy-cluster/;
     make has_installer \
          OCP_VERSION="${ocp_version}"
    )

    if [[ ! -f ${AWS_SHARED_CREDENTIALS_FILE} ]]; then
        _error "AWS credentials file not found in the vault ..."
    fi
}

create_cluster() {
    local cluster_role=$1

    export ARTIFACT_TOOLBOX_NAME_PREFIX="${cluster_role}_ocp_"
    export AWS_DEFAULT_PROFILE=${AWS_DEFAULT_PROFILE:-ci-artifact}
    # ---

    local cluster_name="$(get_config clusters.create.name_prefix)"
    if test_config clusters.create.keep; then
        local author=$(echo "$JOB_SPEC" | jq -r .refs.pulls[0].author)
        cluster_name="${author}-${cluster_role}-$(date +%Y%m%d-%Hh%M)"

        export AWS_DEFAULT_PROFILE="${author}_ci-artifact"
    elif [[ "${PULL_NUMBER:-}" ]]; then
        cluster_name="${cluster_name}-pr${PULL_NUMBER}-${cluster_role}-${BUILD_ID}"
    else
        cluster_name="${cluster_name}-${cluster_role}-$(date +%Hh%M)"
    fi

    export AWS_PROFILE=$AWS_DEFAULT_PROFILE
    echo "Using AWS_[DEFAULT_]PROFILE=$AWS_DEFAULT_PROFILE"

    local install_dir="/tmp/${cluster_role}_ocp_installer"
    rm -rf "$install_dir"
    mkdir -p "$install_dir"

    local install_dir_config="${install_dir}/install-config.yaml"

    cat subprojects/deploy-cluster/utils/install-config.yaml | \
        yq -y '.metadata.name = "'$cluster_name'"' | \
        yq -y '.baseDomain = "'$(get_config clusters.create.ocp.base_domain)'"' | \
        yq -y '.compute[0].platform.aws.type = "'$(get_config clusters.create.ocp.workers.type)'"' | \
        yq -y '.compute[0].replicas = '$(get_config clusters.create.ocp.workers.count) | \
        yq -y '.controlPlane.platform.aws.type = "'$(get_config clusters.create.ocp.control_plane.type)'"' | \
        yq -y '.platform.aws.region = "'$(get_config clusters.create.ocp.region)'"' \
           > "$install_dir_config"

    export PSAP_ODS_SECRET_PATH

    # ensure that the files exist in the vault
    test -f "$PSAP_ODS_SECRET_PATH/pull-secret"
    test -f "$PSAP_ODS_SECRET_PATH/ssh-publickey"

    bash -ce 'sed "s|<PULL-SECRET>|'\''$(cat "$PSAP_ODS_SECRET_PATH/pull-secret")'\''|" -i "'$install_dir_config'"'
    bash -ce 'sed "s|<SSH-KEY>|$(cat "$PSAP_ODS_SECRET_PATH/ssh-publickey")|" -i "'$install_dir_config'"'

    save_install_artifacts() {
        local status=$1

        local install_config="${install_dir}/install-config.back.yaml"
        if [[ -f "$install_config" ]]; then
            yq -yi 'del(.pullSecret)' "$install_config"
            yq -yi 'del(.sshKey)' "$install_config"

            cp "$install_config" "${ARTIFACT_DIR}/${cluster_role}_ocp_install-config.yaml"
        fi

        if [[ "$status" != "success" ]]; then
            _error "$cluster_role OCP cluster creation failed ..."
        fi

        return 0
    }

    # ensure that the cluster's 'metadata.json' is copied
    # to the CONFIG_DEST_DIR even in case of errors
    trap "save_install_artifacts error" ERR SIGTERM SIGINT

    (cd subprojects/deploy-cluster/;
     make cluster \
          OCP_VERSION="$(get_config clusters.create.ocp.version)" \
          CLUSTER_PATH="${install_dir}" \
          CLUSTER_NAME="${cluster_name}" \
          METADATA_JSON_DEST="${CONFIG_DEST_DIR}/${cluster_role}_ocp_metadata.json" \
          DIFF_TOOL= \
         | grep --line-buffered -v 'password\|X-Auth-Token\|UserData:' > "${ARTIFACT_DIR}/${cluster_role}_ocp_install.log"
    )

    cp "${install_dir}/auth/kubeadmin-password" \
       "${CONFIG_DEST_DIR}/${cluster_role}_kubeadmin-password"

    export KUBECONFIG="${CONFIG_DEST_DIR}/${cluster_role}_kubeconfig"

    cp "${install_dir}/auth/kubeconfig" \
       "$KUBECONFIG"

    save_install_artifacts success
}


destroy_cluster() {
    local cluster_role=$1

    export ARTIFACT_TOOLBOX_NAME_PREFIX="${cluster_role}_ocp_"

    local destroy_dir="/tmp/${cluster_role}_ocp_destroy"
    mkdir "$destroy_dir"

    if ! cp "${CONFIG_DEST_DIR}/${cluster_role}_ocp_metadata.json" "${destroy_dir}/metadata.json"; then
        _error "Could not destroy the OCP $cluster_role cluster: cannot prepare the metadata.json file ..."
    fi

    export AWS_PROFILE=${AWS_PROFILE:-ci-artifact}
    export AWS_DEFAULT_PROFILE=${AWS_DEFAULT_PROFILE:-ci-artifact}

    (cd subprojects/deploy-cluster/;
     make uninstall \
          OCP_VERSION="$(get_config clusters.create.ocp.version)" \
          CLUSTER_PATH="${destroy_dir}" \
          >"${ARTIFACT_DIR}/${cluster_role}_ocp_destroy.log" \
          2>&1
    )
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

action="${1:-}"
cluster_role=${2:-}

set -x

case ${action} in
    "prepare_deploy_cluster_subproject")
        prepare_deploy_cluster_subproject
        exit 0
        ;;
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
        ;;
esac
