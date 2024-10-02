#! /bin/bash

set -o pipefail
set -o errexit
set -o nounset
set -o errtrace
set -x

PROJECTS_CLUSTER_SUBPROJECT_DEPLOY_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
TESTING_UTILS_DIR="${PROJECTS_CLUSTER_SUBPROJECT_DEPLOY_DIR}/../../../../testing/utils"

if [[ -z "${TOPSAIL_FROM_CONFIG_FILE:-}" ]]; then
    echo "WARNING: TOPSAIL_FROM_CONFIG_FILE is not set. Commands relying on 'get_config' won't work ..."
    export TOPSAIL_FROM_CONFIG_FILE="/TOPSAIL_FROM_CONFIG_FILE/not/set"
fi

source "$TESTING_UTILS_DIR/process_ctrl.sh"
source "$TESTING_UTILS_DIR/logging.sh"
source "$TESTING_UTILS_DIR/configure.sh"

"$TESTING_UTILS_DIR/ci_init_configure.sh"
# ---

prepare_args_from_pr() {
    set_presets_from_pr_args
    bash "$TESTING_UTILS_DIR/configure_set_presets.sh"
    bash "$TESTING_UTILS_DIR/configure_overrides.sh"
}

capture_gather_extra() {
    local cluster_role=$1

    local base_artifact_dir=$ARTIFACT_DIR

    export ARTIFACT_DIR=$base_artifact_dir/${cluster_role}__gather-extra
    export KUBECONFIG=$CONFIG_DEST_DIR/${cluster_role}_kubeconfig

    "$TESTING_UTILS_DIR"/gather-extra.sh > "$base_artifact_dir/${cluster_role}__gather-extra.log" 2>&1 || true

    export ARTIFACT_DIR=$base_artifact_dir
}

finalize_cluster() {
    local cluster_role=$1

    capture_gather_extra "$cluster_role"

    wait
}

destroy_cluster() {
    local cluster_role=$1

    local cluster_type=$(get_config clusters.create.type)
    if [[ "$cluster_type" == single && "$cluster_role" == driver ]]; then
        echo "Nothing to do to destroy the driver cluster in single mode."
        return
    fi

    finalize_cluster "$cluster_role"

    export KUBECONFIG="${CONFIG_DEST_DIR}/${cluster_role}_kubeconfig"
    if oc get cm/keep-cluster -n default 2>/dev/null; then
        _info "keep-cluster CM found in the default namespace of the $cluster_type/$cluster_role, keep it."
        return
    fi

    if [[ "$cluster_role" == driver ]]; then
        "$PROJECTS_CLUSTER_SUBPROJECT_DEPLOY_DIR/ocp_cluster.sh" destroy "$cluster_role"

    elif ! test_config clusters.sutest.is_managed; then
        "$PROJECTS_CLUSTER_SUBPROJECT_DEPLOY_DIR/ocp_cluster.sh" destroy "$cluster_role"
    else
        if test_config clusters.sutest.managed.is_ocm; then
            "$PROJECTS_CLUSTER_SUBPROJECT_DEPLOY_DIR/osd_cluster.sh" destroy "$cluster_role"
        elif test_config clusters.sutest.managed.is_rosa; then
            _error "cannot destroy ROSA clusters"
        else
            _error "cluster type must be OCM or ROSA"
        fi
    fi
}

create_clusters() {
    local cluster_type=$(get_config clusters.create.type)

    if [[ "$cluster_type" == osd || "$cluster_type" == ocp ]]; then
        if [[ "$cluster_type" == ocp ]]; then
            process_ctrl::run_in_bg "$PROJECTS_CLUSTER_SUBPROJECT_DEPLOY_DIR/ocp_cluster.sh" create sutest

        elif test_config clusters.sutest.managed.is_ocm; then
            process_ctrl::run_in_bg "$PROJECTS_CLUSTER_SUBPROJECT_DEPLOY_DIR/osd_cluster.sh" create sutest

        elif test_config clusters.sutest.managed.is_rosa; then
            _error "cannot create rosa clusters ..."

        else
            _error "managed cluster type must be OCM (or ROSA [unsupported]) ..."
        fi
        process_ctrl::run_in_bg "$PROJECTS_CLUSTER_SUBPROJECT_DEPLOY_DIR/ocp_cluster.sh" create driver

    elif [[ "$cluster_type" == single ]]; then
        process_ctrl::run_in_bg "$PROJECTS_CLUSTER_SUBPROJECT_DEPLOY_DIR/ocp_cluster.sh" create sutest

        echo "Launching a single cluster, creating a symlink for the driver cluster"
        ln -s "${CONFIG_DEST_DIR}/sutest_kubeconfig" "${CONFIG_DEST_DIR}/driver_kubeconfig"

    else
        _error "invalid cluster type: '$cluster_type'"
    fi

    process_ctrl::wait_bg_processes

    # cluster that will be available right away when going to the debug tab of the test pod
    local ci_kubeconfig=${CONFIG_DEST_DIR}/kubeconfig
    if [[ ! -e "$ci_kubeconfig" ]]; then
        ln -s "${CONFIG_DEST_DIR}/driver_kubeconfig" "$ci_kubeconfig"
    fi

    if test_config clusters.create.keep; then
        local KUBECONFIG_DRIVER="${CONFIG_DEST_DIR}/driver_kubeconfig" # cluster driving the test
        local KUBECONFIG_SUTEST="${CONFIG_DEST_DIR}/sutest_kubeconfig" # system under test

        local ocp_region=$(get_config clusters.create.ocp.region)

        # * 'osd' clusters already have their kubeadmin password
        # populated during the cluster bring up
        # * 'single' clusters already have been modified with the
        # keep_cluster call of the sutest cluster.
        if [[ "$cluster_type" == "single" ]]; then
            KUBECONFIG=$KUBECONFIG_SUTEST keep_cluster sutest
        elif [[ "$cluster_type" == "ocp" ]]; then
            KUBECONFIG=$KUBECONFIG_SUTEST keep_cluster sutest
            KUBECONFIG=$KUBECONFIG_DRIVER keep_cluster driver
        fi
    fi
}

destroy_clusters() {
    process_ctrl::run_in_bg destroy_cluster sutest
    process_ctrl::run_in_bg destroy_cluster driver

    process_ctrl::wait_bg_processes
}

keep_cluster() {
    local cluster_role=$1

    echo "Keeping the $cluster_role cluster ..."
    oc create cm keep-cluster -n default --from-literal=keep=true -oyaml --dry-run=client | oc apply -f-

    local pr_author=$(echo "$JOB_SPEC" | jq -r .refs.pulls[0].author)
    local keep_cluster_password_file="$PSAP_ODS_SECRET_PATH/$(get_config secrets.keep_cluster_password_file)"
    ./run_toolbox.py cluster create_htpasswd_adminuser "$pr_author" "$keep_cluster_password_file"

    oc whoami --show-console > "$ARTIFACT_DIR/${cluster_role}_console.link"
    cat <<EOF > "$ARTIFACT_DIR/${cluster_role}_oc-login.cmd"
source "\$PSAP_ODS_SECRET_PATH/get_cluster.password"
oc login $(oc whoami --show-server) --insecure-skip-tls-verify --username=$pr_author --password="\$password"
EOF

    local cluster_region=$(oc get machines -n openshift-machine-api -ojsonpath={.items[0].spec.providerSpec.value.placement.region})
    local cluster_tag=$(oc get machines -n openshift-machine-api -ojsonpath={.items[0].spec.providerSpec.value.tags[0].name} | cut -d/ -f3)

    cat <<EOF > "$ARTIFACT_DIR/${cluster_role}_destroy_cluster.cmd"
./run_toolbox.py cluster destroy_ocp $cluster_region $cluster_tag
EOF
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

    local action="${1:-}"

    set -x
    case ${action} in
        "create")
            process_ctrl__finalizers+=("process_ctrl::kill_bg_processes")
            prepare_args_from_pr
            if [[ "$(type -t clusters_create__check_test_size)" == function ]]; then
                if ! clusters_create__check_test_size; then
                    # shouldn't be reached
                    _error "Cannot create the cluster, see clusters_create__check_test_size logs"
                    exit 1
                fi
            else
                _warning "No 'clusters_create__check_test_size' function defined to validate the size of the cluster being created."
            fi

            "$PROJECTS_CLUSTER_SUBPROJECT_DEPLOY_DIR/ocp_cluster.sh" prepare_deploy_cluster_subproject

            create_clusters
            exit 0
            ;;
        "destroy")
            set +o errexit # do not exit on error when destroying the resources

            prepare_args_from_pr

            "$PROJECTS_CLUSTER_SUBPROJECT_DEPLOY_DIR/ocp_cluster.sh" prepare_deploy_cluster_subproject

            destroy_clusters
            exit 0
            ;;
        "keep")
            if [[ -z "${PSAP_ODS_SECRET_PATH:-}" ]]; then
                echo "PSAP_ODS_SECRET_PATH is not set, using the default value."
                export PSAP_ODS_SECRET_PATH=/run/psap-ods-secret-1
            fi
            if ! [[ -d $PSAP_ODS_SECRET_PATH ]]; then
                echo "ERROR: PSAP_ODS_SECRET_PATH=$PSAP_ODS_SECRET_PATH is not a directory ..."
                exit 1
            fi
            keep_cluster cluster
            ;;
        *)
            _error "Unknown action '$action'"
            ;;
    esac
}

main "$@"
