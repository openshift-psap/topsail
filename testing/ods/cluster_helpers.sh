cluster_helpers::ocm_login() {
    export OCM_ENV
    export PSAP_ODS_SECRET_PATH

    # do it in a subshell to avoid leaking the `OCM_TOKEN` secret because of `set -x`
    bash -c '
      set -o errexit
      set -o nounset

      OCM_TOKEN=$(cat "$PSAP_ODS_SECRET_PATH/ocm.token" | grep "^${OCM_ENV}=" | cut -d= -f2-)
      echo "Login in $OCM_ENV with token length=$(echo "$OCM_TOKEN" | wc -c)"
      exec ocm login --token="$OCM_TOKEN" --url="$OCM_ENV"
      '
}

cluster_helpers::ocm_oc_login() {
    osd_cluster_name=$1

    export PSAP_ODS_SECRET_PATH
    export API_URL=$(ocm describe cluster "$osd_cluster_name" --json | jq -r .api.url)

    # do it in a subshell to avoid leaking the `KUBEADMIN_PASS` secret because of `set -x`
    bash -c '
    source "$PSAP_ODS_SECRET_PATH/create_osd_cluster.password"
    oc login "$API_URL" \
             --username=kubeadmin \
             --password="$KUBEADMIN_PASS" \
             --insecure-skip-tls-verify
    '
}

cluster_helpers::ocm_cluster_is_ready() {
    osd_cluster_name=$1

    [[ $((ocm describe cluster "$osd_cluster_name"  --json || true) | jq -r .state) == "ready" ]];
}

cluster_helpers::get_osd_cluster_name() {
    cluster_role=$1

    if [[ "${OSD_CLUSTER_NAME}" ]]; then
        echo "$OSD_CLUSTER_NAME"
        return
    fi

    cat "${SHARED_DIR:-}/osd_${cluster_role}_cluster_name" 2>/dev/null || true
}

cluster_helpers::get_cluster_is_rosa() {
    cluster_role=$1

    if [[ "${OSD_CLUSTER_IS_ROSA}" ]]; then
        echo "$OSD_CLUSTER_IS_ROSA"
        return
    fi

    cat "${SHARED_DIR:-}/osd_${cluster_role}_cluster_is_rosa" 2>/dev/null || true
}

cluster_helpers::get_compute_node_count() {
    cluster_role=$1
    shift
    cluster_type=$1
    shift
    instance_type=$1
    shift

    if [[ "$cluster_role" == "sutest" && "$SUTEST_FORCE_COMPUTE_NODES_COUNT" ]]; then
        echo "$SUTEST_FORCE_COMPUTE_NODES_COUNT"
        return

    elif [[ "$cluster_role" == "driver" && "$DRIVER_FORCE_COMPUTE_NODES_COUNT" ]]; then
        echo "$DRIVER_FORCE_COMPUTE_NODES_COUNT"
        return

    elif [[ "$cluster_role" == "sutest" && "$SUTEST_ENABLE_AUTOSCALER" ]]; then
        echo 2
        return
    fi

    if [[ "$cluster_role" == "sutest" ]]; then
        notebook_size="$ODS_NOTEBOOK_CPU_SIZE $ODS_NOTEBOOK_MEMORY_SIZE_GI"
    else
        notebook_size="$ODS_TESTPOD_CPU_SIZE $ODS_TESTPOD_MEMORY_SIZE_GI"
    fi

    size=$(bash -c "python3 $THIS_DIR/sizing/sizing '$instance_type' '$ODS_CI_NB_USERS' $notebook_size >&2 > '${ARTIFACT_DIR:-/tmp}/${cluster_role}_${cluster_type}_sizing'; echo \$?")

    if [[ "$size" == 0 ]]; then
        echo "ERROR: couldn't determine the number of nodes to request ..." >&2
        false
    fi

    echo "$size"
}

cluster_helpers::get_compute_node_type() {
    cluster_role=$1
    shift
    cluster_type=$1

    if [[ "$cluster_role" == "sutest" ]]; then
        if [[ "$cluster_type" == "ocp" ]]; then
            echo "$OCP_SUTEST_COMPUTE_MACHINE_TYPE"
        else
            echo "$OSD_SUTEST_COMPUTE_MACHINE_TYPE"
        fi
    else
        echo "$DRIVER_COMPUTE_MACHINE_TYPE"
    fi
}

cluster_helpers::connect_sutest_cluster() {
    osd_cluster_name=$1

    touch "$KUBECONFIG_SUTEST"

    switch_sutest_cluster

    if [[ "$osd_cluster_name" ]]; then
        echo "OSD cluster name is $osd_cluster_name"

        cluster_helpers::ocm_login

        if ! cluster_helpers::ocm_cluster_is_ready "$osd_cluster_name"
        then
            echo "OCM cluster '$osd_cluster_name' isn't ready ..."
            exit 1
        fi

        cluster_helpers::ocm_oc_login "$osd_cluster_name"
    fi

    oc get clusterversion
}
