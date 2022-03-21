#! /usr/bin/env bash

set -x
set -o pipefail
set -o errexit
set -o nounset

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
        echo "ERROR: Sample rate ($sample_rate) below minimum expected ($MINSR)"
        return 1
    fi
    echo "Sample rate test passed!"
    if [[ "$MAXDR" -lt "$bench_duration" ]] ; then
        echo "ERROR: Benchmark duration ($bench_duration) above maximum expected ($MAXDR)"
        return 1
    fi
    echo "Benchmark duration test passed!"
    return 0
}

THIS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

source $THIS_DIR/../prow/gpu-operator.sh source

# WDM_DEPENDENCY_FILE exported in ^^^^
./toolbox/wdm ensure has_gpu_operator

gpu_node_hostname=$(oc get nodes -oname -lfeature.node.kubernetes.io/pci-10de.present -ojsonpath={.items[].metadata.labels} | jq -r '.["kubernetes.io/hostname"]')

if [ -z "$gpu_node_hostname" ]; then
    echo "Couldn't find the GPU node ..."
    oc get nodes --show-labels | sed 's|,|,- |g' | tr ',' '\n'
    exit 1
else
    echo "Using GPU node name: $gpu_node_hostname"
fi

DL_OPT=""
if [[ "$@" == *use_private_s3* ]]; then
    S3_CRED="${PSAP_SECRET_PATH}/cococred.csv"
    DL_OPT="--s3_cred=$S3_CRED"
fi

RUN_CNT=1
if [[ "$@" == *download_twice* ]]; then
    # for testing purposes, to make sure that the files are cached and not actually downloaded twice
    RUN_CNT=2
fi

for i in $(seq $RUN_CNT); do
    ./run_toolbox.py benchmarking download_coco_dataset "$gpu_node_hostname" $DL_OPT
done

RUN_CNT=1
if [[ "$@" == *benchmark_twice* ]]; then
    # for testing purposes, to make sure that the files are cached and not actually downloaded twice
    RUN_CNT=2
fi

for i in $(seq $RUN_CNT); do
    ./run_toolbox.py benchmarking run_mlperf_ssd "$gpu_node_hostname" --epochs=$EPOCHS --threshold=$THRESHOLD
    if ! assess_benchmark_stats; then
        exit 1
    fi
done
