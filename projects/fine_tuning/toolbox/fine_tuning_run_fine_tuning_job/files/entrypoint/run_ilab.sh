# !/bin/bash

set -o pipefail
set -o errexit
set -o nounset
set -o errtrace
set -x

CACHE_DIR=/mnt/output/cache

#export TRANSFORMERS_CACHE=$CACHE_DIR
export TRITON_CACHE_DIR=$CACHE_DIR
export XDG_CACHE_HOME=$CACHE_DIR
export HF_HOME=$CACHE_DIR

export TRITON_HOME=$CACHE_DIR
export TRITON_DUMP_DIR=$TRITON_HOME
export TRITON_CACHE_DIR=$TRITON_HOME
export TRITON_OVERRIDE_DIR=$TRITON_HOME

mkdir -p "$CACHE_DIR"

if [[ "${NCCL_SOCKET_IFNAME:-}" ]]; then

    export NCCL_IB_DISABLE=1
    export NCCL_NET="socket"
    export NCCL_IBEXT_DISABLE=1

    echo "NCCL_SOCKET_IFNAME=$NCCL_SOCKET_IFNAME is set. Need to agree on the the new address ... (old address: $MASTER_ADDR)"

    SHARED_FILE=/mnt/storage/ip
    if [[ $RANK == 0 ]]; then
        MASTER_ADDR=$(ip route | grep "$NCCL_SOCKET_IFNAME" | grep src | cut -d" " -f9)
        echo "New address is $MASTER_ADDR. Saving it in the shared storage ..."
        # this relies on the fact that the `master` Pod starts before
        # the worker Pods.  This is enforced by the PyTorchJob, which
        # make the worker nodes wait for the master hostname to
        # resolve correctly.
        echo $MASTER_ADDR > "$SHARED_FILE"
    else
        MASTER_ADDR=$(cat "$SHARED_FILE")
        echo "New address $MASTER_ADDR found in the shared storage."
    fi

    #ulimit -l unlimited

    export MASTER_ADDR
    export PET_MASTER_ADDR=$MASTER_ADDR
fi

echo "Removing CUDA-Compat library from LD_LIBRARY_PATH ..."
export LD_LIBRARY_PATH=$(echo $LD_LIBRARY_PATH | sed s+/usr/local/cuda/compat++)

echo "STARTING TORCHRUN | $(date)"
SECONDS=0
ret=0
if ! torchrun \
    --node_rank "${RANK}" \
    --rdzv_endpoint "${MASTER_ADDR}:${MASTER_PORT}" \
    $(cat "$CONFIG_JSON_PATH" | jq -r '. | to_entries | .[] | ("--" + .key + " " + (.value | tostring))' | sed "s/ true//");
then
    ret=1
    echo "TORCHRUN FAILED :/ (retcode=$ret)"
fi
echo "TORCHRUN FINISHED after $SECONDS seconds | $(date)"

exit $ret
