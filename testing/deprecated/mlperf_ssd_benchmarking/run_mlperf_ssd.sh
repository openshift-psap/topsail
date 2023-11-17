#! /usr/bin/env bash

set -x
set -o pipefail
set -o errexit
set -o nounset

THIS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

source $THIS_DIR/../prow/gpu-operator.sh source
source $THIS_DIR/../prow/cluster.sh source
finalizers+=("collect_must_gather")

PSAP_SECRET_PATH=/var/run/psap-entitlement-secret
EPOCHS=3
THRESHOLD=0.05
MINSR=150.0
MAXDR=30


assess_benchmark_stats () {
    artifact_dir=${ARTIFACT_DIR:-"/tmp/ci-artifacts_$(date +%Y%m%d)"}
    sample_rate=$(cat "${artifact_dir}/benchmarking_run_ssd_sample_rate.log" | cut -d" " -f1)
    bench_duration=$(cat "${artifact_dir}/benchmarking_run_ssd_bench_duration.log" | cut -d" " -f1)
    if (( $(echo "$MINSR > $sample_rate" |bc -l) )) ; then
        _error "benchmarking_sample_rate_below_minimum" "Sample rate ($sample_rate) below minimum expected ($MINSR)"
        return 1
    fi
    echo "Sample rate test passed!"

    if [[ "$MAXDR" -lt "$bench_duration" ]] ; then
        _error "benchmarking_duration_above_maximum" "Benchmark duration ($bench_duration) above maximum expected ($MAXDR)"
        return 1
    fi
    echo "Benchmark duration test passed!"

    _info "benchmarking_results_ok" "Benchmarking results: $bench_duration minutes, $sample_rate samples/sec"

    return 0
}

# ---

if ! dtk_image_is_valid; then
    _flake "dtk_image_not_valid" "DriverToolkit is not valid, cannot continue."
    exit 1
fi

./topsail/wdm ensure library.gpu-operator.has_gpu_operator --library
GPU_NODE_CONFIG=--config=instance_type=g4dn.xlarge,instance_count=1
./topsail/wdm ensure library.gpu.has_gpu_nodes --library $GPU_NODE_CONFIG
./topsail/wdm ensure library.gpu-operator.is_ready --library

gpu_node_hostname=$(oc get nodes -oname -lfeature.node.kubernetes.io/pci-10de.present -ojsonpath={.items[].metadata.labels} | jq -r '.["kubernetes.io/hostname"]')

if [ -z "$gpu_node_hostname" ]; then
    echo "Couldn't find the GPU node ..."
    oc get nodes --show-labels | sed 's|,|,- |g' | tr ',' '\n'
    _error "no_gpu_node" "Couldn't find a GPU node in the cluster ..."
    exit 1
fi

echo "Using GPU node name: $gpu_node_hostname"

DL_OPT=""
if [[ "$@" == *use_private_s3* ]]; then
    S3_CRED="${PSAP_SECRET_PATH}/cococred.csv"
    DL_OPT="--s3_cred=$S3_CRED"
fi

./run_toolbox.py benchmarking download_coco_dataset "$gpu_node_hostname" $DL_OPT

./run_toolbox.py benchmarking run_mlperf_ssd "$gpu_node_hostname" --epochs=$EPOCHS --threshold=$THRESHOLD
assess_benchmark_stats
