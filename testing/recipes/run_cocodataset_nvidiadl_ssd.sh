#! /usr/bin/env bash

set -x
set -o pipefail
set -o errexit
set -o nounset

THIS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

PSAP_SECRET_PATH=/var/run/psap-entitlement-secret

source $THIS_DIR/../prow/gpu-operator.sh source

prepare_cluster_for_gpu_operator

gpu_node_hostname=$(oc get nodes -oname -lfeature.node.kubernetes.io/pci-10de.present -ojsonpath={.items[].metadata.labels} | jq -r '.["kubernetes.io/hostname"]')

if [ -z "$gpu_node_hostname" ]; then
    echo "Couldn't find the GPU node ..."
    oc get nodes --show-labels | sed 's|,|,- |g' | tr ',' '\n'
    exit 1
else
    echo "Using GPU node name: $gpu_node_hostname"
fi

./run_toolbox.py gpu_operator deploy_from_operatorhub
./run_toolbox.py gpu_operator wait_deployment

DL_OPT=""
if [[ "$@" == *use_mirror* ]]; then
   DL_OPT="${DL_OPT} --mirror_base_url=https://mirror-dataset.apps.ci-mirror.psap.aws.rhperfscale.org/coco"
   DL_OPT="${DL_OPT} --client-cert=${PSAP_SECRET_PATH}/entitled-mirror-client-creds.pem"
fi

RUN_CNT=1
if [[ "$@" == *download_twice* ]]; then
    # for testing purposes, to make sure that the files are cached and not actually downloaded twice
    RUN_CNT=2
fi

for i in $(seq $RUN_CNT); do
    ./run_toolbox.py benchmarking download_coco_dataset "$gpu_node_hostname" $DL_OPT
done

./run_toolbox.py benchmarking run_nvidiadl_ssd "$gpu_node_hostname"
