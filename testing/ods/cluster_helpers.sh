if [ -n "$BASH_VERSION" ]; then
    # assume Bash
    TESTING_ODS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
elif [ -n "$ZSH_VERSION" ]; then
    # assume ZSH
    TESTING_ODS_DIR=${0:a:h}
elif [[ -z "${TESTING_ODS_DIR:-}" ]]; then
     echo "Shell isn't bash nor zsh, please expose the directory of this file with TESTING_ODS_DIR."
     false
fi

cluster_helpers::ocm_login() {
    local ocm_env=$(get_config clusters.sutest.managed.env)

    # do it in a subshell to avoid leaking the `OCM_TOKEN` secret because of `set -x`
    bash -c '
      set -o errexit
      set -o nounset

      OCM_TOKEN=$(cat "'$PSAP_ODS_SECRET_PATH'/ocm.token" | grep "^'${ocm_env}'=" | cut -d= -f2-)
      echo "Login in '$ocm_env' with token length=$(echo "$OCM_TOKEN" | wc -c)"
      exec ocm login --token="$OCM_TOKEN" --url="'$ocm_env'"
      '
}

cluster_helpers::get_compute_node_count() {
    local cluster_role=$1

    if [[ "$cluster_role" == "sutest" ]]; then
        local NB_SIZE_CONFIG_KEY=rhods.notebooks.customize.notebook_size
        local notebook_size="$(get_config $NB_SIZE_CONFIG_KEY.cpu) $(get_config $NB_SIZE_CONFIG_KEY.mem_gi)"

        if test_config clusters.sutest.is_managed; then
            if test_config clusters.sutest.managed.is_ocm; then
                local instance_type="$(get_config clusters.create.ocm.compute.type)"
            else
                _error "Cannot get the instance type of ROSA clusters ..."
            fi
        else
            local instance_type="$(get_config clusters.create.ocp.compute.type)"
        fi

    else
        notebook_size="$(get_config tests.notebooks.test_pods.size.cpu) $(get_config tests.notebooks.test_pods.size.mem_gi)"
        local instance_type="$(get_config clusters.create.ocp.compute.type)"
    fi

    local user_count=$(get_config tests.notebooks.users.count)

    local size=$(bash -c "python3 $TESTING_ODS_DIR/sizing/sizing \
                   '$instance_type' \
                   '$user_count' \
                   $notebook_size \
                    >&2 \
                    > '${ARTIFACT_DIR:-/tmp}/${cluster_role}_sizing'; echo \$?")

    if [[ "$size" == 0 ]]; then
        echo "ERROR: couldn't determine the number of nodes to request ..." >&2
        false
    fi

    echo "$size"
}

cluster_helpers::ocm_oc_login() {
    local managed_cluster_name=$(get_config clusters.sutest.managed.name)

    local api_url=$(ocm describe cluster "$managed_cluster_name" --json | jq -r .api.url)

    # do it in a subshell to avoid leaking the `KUBEADMIN_PASS` secret because of `set -x`
    bash -c '
    source "'$PSAP_ODS_SECRET_PATH'/create_osd_cluster.password"
    oc login "'$api_url'" \
             --username=kubeadmin \
             --password="$KUBEADMIN_PASS" \
             --insecure-skip-tls-verify
    '
}

cluster_helpers::connect_sutest_cluster() {
    touch "$KUBECONFIG_SUTEST"

    switch_sutest_cluster

    if ! test_config clusters.sutest.is_managed; then
        oc get clusterversion

        return
    fi

    local managed_cluster_name=$(get_config clusters.sutest.managed.name)
    if test_config clusters.sutest.managed.is_ocm; then

        cluster_helpers::ocm_login

        if ! [[ $((ocm describe cluster "$osd_cluster_name"  --json || true) | jq -r .state) == "ready" ]];
        then
            _error "OCM cluster '$managed_cluster_name' isn't ready ..."
        fi

        cluster_helpers::ocm_oc_login
    fi

    oc get clusterversion
}
