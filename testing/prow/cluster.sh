#! /usr/bin/env bash

set -o pipefail
set -o errexit
set -o nounset

THIS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd ${THIS_DIR}/../..

cluster_upgrade() {
    if [ -z "${CLUSTER_UPGRADE_TARGET_IMAGE:-}" ]; then
        echo "FATAL: CLUSTER_UPGRADE_TARGET_IMAGE must be provided to upgrade the cluster"
        exit 1
    fi
    ./run_toolbox.py cluster upgrade_to_image "$CLUSTER_UPGRADE_TARGET_IMAGE"
}

dtk_image_is_valid() {
    MINI_POD_SPEC='{"apiVersion": "v1", "kind":"Pod","metadata":{"name":"test"},"spec":{"containers":[{"name":"cnt"}]}}'
    DTK_IMAGE="image-registry.openshift-image-registry.svc:5000/openshift/driver-toolkit:latest"

    dtk_release=$(oc debug -f <(echo "$MINI_POD_SPEC") \
                     --quiet \
                     -n default \
                     --image=${DTK_IMAGE} \
                     -- \
                     cat /etc/driver-toolkit-release.json)
    dtk_kernel=$(echo "$dtk_release" | jq -r .KERNEL_VERSION)

    node_kernel=$(oc get nodes -ojsonpath={.items[].status.nodeInfo.kernelVersion})

    echo "Driver toolkit 'latest' image kernel: ${dtk_kernel}"
    echo "Nodes kernel: ${node_kernel}"

    [[ "${dtk_kernel}" == "${node_kernel}" ]]
}

if [ -z "${1:-}" ]; then
    echo "FATAL: $0 expects at least 1 argument ..."
    exit 1
fi

action="${1:-}"
shift

set -x

case ${action} in
    "upgrade")
        cluster_upgrade
        exit 0
        ;;
    "source")
        # file is being sourced by another script
        echo "INFO: Cluster CI entrypoint has been sourced"
        ;;
    *)
        echo "FATAL: Action not supported: '$action')"
        exit 1
        ;;
esac
