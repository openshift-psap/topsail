#! /usr/bin/env bash

set -x
set -o pipefail
set -o errexit
set -o nounset

THIS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

PSAP_SECRET_PATH=/var/run/psap-entitlement-secret

source $THIS_DIR/../nightly/gpu-operator.sh source

prepare_cluster_for_gpu_operator

gpu_node_hostname=$(oc get nodes -oname -lnode.kubernetes.io/instance-type=g4dn.xlarge -ojsonpath={.items[].metadata.labels} | jq -r '.["kubernetes.io/hostname"]')

if [ -z "$gpu_node_hostname" ]; then
    echo "Couldn't find the GPU node ..."
    oc get nodes --show-labels | sed 's|,|,- |g' | tr ',' '\n'
    exit 1
else
    echo "Using GPU node name: $gpu_node_hostname"
fi

./run_toolbox.py gpu_operator deploy_from_operatorhub --namespace openshift-operators
./run_toolbox.py gpu_operator wait_deployment

for i in 1 2; do
    ./run_toolbox.py benchmarking download_coco_dataset \
                     "$gpu_node_hostname" \
                     --mirror_base_url=https://mirror-dataset.apps.ci-mirror.psap.aws.rhperfscale.org/coco \
                     --client-cert=${PSAP_SECRET_PATH}/entitled-mirror-client-creds.pem
done

./run_toolbox.py benchmarking run_nvidiadl_ssd "$gpu_node_hostname"
