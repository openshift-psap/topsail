#! /bin/bash

set -o pipefail
set -o errexit
set -o nounset
set -o errtrace
set -x

PROJECTS_THIS_SUBPROJECT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
TOPSAIL_DIR="$PROJECTS_THIS_SUBPROJECT_DIR/../../../.."
TESTING_UTILS_DIR="$TOPSAIL_DIR/testing/utils"

source "$TESTING_UTILS_DIR/logging.sh"
source "$TESTING_UTILS_DIR/configure.sh"

DEPLOY_CLUSTER_DIR=projects/cluster/subprojects/deploy-cluster

# ---

export AWS_SHARED_CREDENTIALS_FILE="${PSAP_ODS_SECRET_PATH:-}/.awscred"

prepare_deploy_cluster_subproject() {
    cp "$DEPLOY_CLUSTER_DIR"/utils/config.mk{.sample,}
    cp "$DEPLOY_CLUSTER_DIR"/utils/install-config.yaml{.sample,}

    local ocp_version=$(get_config clusters.create.ocp.version)

    local DOWNLOAD_OCP_INSTALLER_FROM_PRIVATE=
    if [[ "$DOWNLOAD_OCP_INSTALLER_FROM_PRIVATE" ]]; then
        mkdir -p "$DEPLOY_CLUSTER_DIR/utils/installers/$ocp_version"
        wget --quiet "https://people.redhat.com/~kpouget/22-10-05/openshift-install-linux-$ocp_version.tar.gz"
        tar xzf "openshift-install-linux-$ocp_version.tar.gz" openshift-install
        mv openshift-install "$DEPLOY_CLUSTER_DIR/utils/installers/$ocp_version/openshift-install"
        rm "openshift-install-linux-$ocp_version.tar.gz"
    fi

    (cd "$DEPLOY_CLUSTER_DIR"/;
     make has_installer \
          OCP_VERSION="${ocp_version}"
    )

    if [[ ! -f ${AWS_SHARED_CREDENTIALS_FILE} ]]; then
        _error "AWS credentials file not found in the vault ..."
    fi
}

cluster_cost_command() {
    local cluster_name=$1

    local cluster_ticket=$(get_config clusters.create.ocp.tags.TicketId)

    if [[ "$cluster_ticket" == null || -z "$cluster_ticket" ]]; then
        echo "No TicketId, cannot check its cost" > "${ARTIFACT_DIR}/no_ticket_id"
        return
    fi

    cat <<EOF
account_id=\$(cat \$PSAP_ODS_SECRET_PATH/.awscred | grep 'account id' | cut -d' ' -f4)
curl -k -Ssf 'https://cloud-governance-stage.rdu2.scalelab.redhat.com:8000/api/v1/cloud_governance/get_cluster_details?account_id=\${account_id}&cluster_name=${cluster_name}' | jq
EOF
}

create_cluster() {
    local cluster_role=$1

    export ARTIFACT_TOOLBOX_NAME_PREFIX="${cluster_role}_ocp_"

    # ---

    if [[ "${OPENSHIFT_CI:-}" == true ]]; then
        local author=$(echo "$JOB_SPEC" | jq -r .refs.pulls[0].author)

        if [[ -z "$author" ]]; then
            _error "Couldn't figure out the test author from $JOB_SPEC ..."
        fi
    else
        _error "Don't know how to find out the PR author outside of OpenShift CI ..."
    fi

    local cluster_name_prefix="$(get_config clusters.create.name_prefix)"
    if test_config clusters.create.keep; then
        cluster_name="${cluster_name_prefix}-"
        cluster_date="$(date +%Y%m%d-%Hh%M)"
        if [[ $(get_config clusters.create.type) == single ]]; then
            cluster_name="${cluster_date}-${cluster_name_prefix}-${author}"
        else
            cluster_name="${cluster_date}-${cluster_role}-${author}"
        fi
    elif [[ "${PULL_NUMBER:-}" ]]; then
        cluster_name="${cluster_name_prefix}-pr${PULL_NUMBER}-${cluster_role}-${BUILD_ID}"
    else
        cluster_name="${cluster_name_prefix}-${cluster_role}-$(date +%Hh%M)"
    fi

    local install_dir="/tmp/${cluster_role}_ocp_installer"
    rm -rf "$install_dir"
    mkdir -p "$install_dir"

    local install_dir_config="${install_dir}/install-config.yaml"

    cat "$DEPLOY_CLUSTER_DIR"/utils/install-config.yaml | \
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

    local deploy_cluster_target=$(get_config clusters.create.ocp.deploy_cluster.target)

    cluster_use_fips=""
    if test_config clusters.create.ocp.use_fips; then
        local cluster_use_fips="true"
    fi

    local cluster_tags=$(get_config clusters.create.ocp.tags)
    if [[ "$cluster_tags" == "null" || "$cluster_tags" == "{}" ]]; then
        machine_tags="{}"
    else
        machine_tags=$((echo "$cluster_tags") | jq . --compact-output)
    fi

    author_kerberos=$(cat OWNERS| yq ".cluster_create.$author" -r) # gh id -> RH kerb id
    if [[ "$author_kerberos" == null ]]; then
        _error "PR author '$author' not found in the OWNERS's file 'cluster_create' group."
    fi

    ticketId=$(echo "$machine_tags" | jq .TicketId)
    if [[ "$ticketId" == null ]]; then
        _error "clusters.create.ocp.tags.TicketId must be defined to create the cluster"
    fi

    machine_tags=$(echo "$machine_tags" | jq ". += {User: \"$author_kerberos\"}" --compact-output)

    launch_time=$(date "+%Y/%m/%d %H:%M:%S %Z")
    machine_tags=$(echo "$machine_tags" | jq ". += {LaunchTime: \"$launch_time\"}" --compact-output)

    time_to_live=$(echo "$machine_tags" | jq .TimeToLive)
    if [[ "$time_to_live" == null ]]; then
        time_to_live="12 hours"
        echo "WARNING: 'TimeToLive' tag not found. Setting the default duration: $time_to_live"
        machine_tags=$(echo "$machine_tags" | jq ". += {TimeToLive: \"$time_to_live\"}" --compact-output)
    else
        echo "INFO: Found the 'TimeToLive' tag: '$time_to_live'"
    fi
    echo "$time_to_live" > "${ARTIFACT_DIR}/${cluster_role}_tag_TimeToLive"

    cluster_user_identifier=$(echo "$machine_tags" | jq .ClusterUserIdentifier)
    if [[ "$cluster_user_identifier" == null ]]; then
        cluster_user_identifier="${author_kerberos}@${REPO_OWNER:-}_${REPO_NAME:-}/${PULL_NUMBER:-}/${JOB_NAME:-}/${BUILD_ID:-}/artifacts/${JOB_NAME_SAFE:-}"
        echo "INFO: 'ClusterUserIdentifier' tag not found. Setting the default duration: $cluster_user_identifier"
        machine_tags=$(echo "$machine_tags" | jq ". += {\"ClusterUserIdentifier\": \"$cluster_user_identifier\"}" --compact-output)
    else
        echo "INFO: Found a 'ClusterUserIdentifier' tag: '$cluster_user_identifier'"
    fi
    echo "$cluster_user_identifier" > "${ARTIFACT_DIR}/${cluster_role}_tag_ClusterUserIdentifier"

    use_spot=""
    if test_config clusters.create.ocp.workers.spot; then
        use_spot=y
    fi

    # ensure that the cluster's 'metadata.json' is copied
    # to the CONFIG_DEST_DIR even in case of errors
    trap "save_install_artifacts error" ERR SIGTERM SIGINT

    (cd "$DEPLOY_CLUSTER_DIR"/;
     make "$deploy_cluster_target" \
          OCP_VERSION="$(get_config clusters.create.ocp.version)" \
          CLUSTER_PATH="${install_dir}" \
          CLUSTER_NAME="${cluster_name}" \
          METADATA_JSON_DEST="${CONFIG_DEST_DIR}/${cluster_role}_ocp_metadata.json" \
          DIFF_TOOL= \
          USE_SPOT=$use_spot \
          USE_FIPS="${cluster_use_fips}" \
          MACHINE_TAGS="${machine_tags}" \
         | grep --line-buffered -v 'password\|X-Auth-Token\|UserData:' > "${ARTIFACT_DIR}/${cluster_role}_ocp_install.log"
    )

    cp "${install_dir}/auth/kubeadmin-password" \
       "${CONFIG_DEST_DIR}/${cluster_role}_kubeadmin-password"

    export KUBECONFIG="${CONFIG_DEST_DIR}/${cluster_role}_kubeconfig"

    cp "${install_dir}/auth/kubeconfig" \
       "$KUBECONFIG"

    save_install_artifacts success

    cluster_cost_command "$cluster_name"> "${ARTIFACT_DIR}/${cluster_role}__cluster_cost.cmd"
}


destroy_cluster() {
    local cluster_role=$1

    export ARTIFACT_TOOLBOX_NAME_PREFIX="${cluster_role}_ocp_"

    local destroy_dir="/tmp/${cluster_role}__ocp_destroy"
    mkdir "$destroy_dir"

    if ! cp "${CONFIG_DEST_DIR}/${cluster_role}_ocp_metadata.json" "${destroy_dir}/metadata.json"; then
        _error "Could not destroy the OCP $cluster_role cluster: cannot prepare the metadata.json file ..."
    fi

    (cd "$DEPLOY_CLUSTER_DIR"/;
     make uninstall \
          OCP_VERSION="$(get_config clusters.create.ocp.version)" \
          CLUSTER_PATH="${destroy_dir}" \
          >"${ARTIFACT_DIR}/${cluster_role}_ocp_destroy.log" \
          2>&1
    )
}

# ---

main() {
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
}

main "$@"
