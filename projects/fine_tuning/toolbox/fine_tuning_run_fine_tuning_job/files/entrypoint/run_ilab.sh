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

if [[ "${WITH_RDMA:-}" ]]; then
  export NCCL_TOPO_FILE=/mnt/storage/topo.xml
  num_rdma=$(ls /sys/class/infiniband/ | wc -l)
  IFS=',' read -ra ADDR <<< "$NCCL_SOCKET_IFNAME"   # Split by comma
  length=${#ADDR[@]}  # Get the length (number of elements in the array)
  echo "Length of NCCL_SOCKET_IFNAME: $length"
  NCCL_IB_HCA=''
  for idx in $(seq $((num_rdma-1)) -1 $((num_rdma-length))); do
    # Append the value to the NCCL_IB_HCA string
    if [ -z "$NCCL_IB_HCA" ]; then
      NCCL_IB_HCA="mlx5_$idx"  # Initialize the string with the first value
    else
      NCCL_IB_HCA="$NCCL_IB_HCA,mlx5_$idx"  # Append the next value with a comma
    fi
  done
  export NCCL_IB_HCA="$NCCL_IB_HCA"
  export NCCL_IB_DISABLE=0
  export NCCL_IB_GID_INDEX=3
  export NCCL_DEBUG=info
  echo "Using $length SR-IOV NIC’s with rdma"
fi

if [[ "${NCCL_SOCKET_IFNAME:-}" ]]; then


    MAPPING="$(cat /mnt/nic-mapping/nodename_ip_mapping.yaml)"
    for ifname in $(echo $NCCL_SOCKET_IFNAME | tr , " "); do
        current_ip=$(ip route | grep "$ifname " | cut -d" " -f9)
        correct_ip=$(echo "$MAPPING" | grep "$NODE_HOSTNAME" | grep "$ifname:" | cut -d: -f4)

        echo "Remapping $ifname from $current_ip to $correct_ip"
        # will fail without a privileged container ...
        ip addr del "$current_ip/24" dev "$ifname"
        ip addr add "$correct_ip/24" dev "$ifname"

        #while read remote_mapping; do
        #    remote_ip=$(echo "$remote_mapping" | cut -d: -f4)
        #    remote_host=$(echo "$remote_mapping" | cut -d: -f1)
        #    echo "Adding route from $correct_ip to $remote_ip on $remote_host"
        #    ip route add $remote_ip/32 via "$correct_ip" metric 150
        #done <<< $(echo "$MAPPING" | grep -v "$NODE_HOSTNAME" |  grep "$ifname:")
    done

    if [[ "$USE_PRIMARY_NIC" == "True" ]]; then
        primary_nic_name=$(ip addr | grep ": eth0" | tr : " " | awk '{ print $2}')
        export NCCL_SOCKET_IFNAME="$primary_nic_name,$NCCL_SOCKET_IFNAME"
    fi

    echo "Using NCCL_SOCKET_IFNAME=$NCCL_SOCKET_IFNAME"
fi

config_json=$(jq . "$CONFIG_JSON_PATH")

NCCL_SOCKET_NTHREADS=$(echo "$config_json" | jq -r .NCCL_SOCKET_NTHREADS)
if [[ "$NCCL_SOCKET_NTHREADS" ]]; then
    echo "Using NCCL_SOCKET_NTHREADS=$NCCL_SOCKET_NTHREADS"
    export NCCL_SOCKET_NTHREADS

    # remove NCCL_SOCKET_NTHREADS from the config
    config_json=$(echo "$config_json" | jq "del(.NCCL_SOCKET_NTHREADS)")
else
    # just for consistency
    unset NCCL_SOCKET_NTHREADS
fi

echo "Removing CUDA-Compat library from LD_LIBRARY_PATH ..."
export LD_LIBRARY_PATH=$(echo $LD_LIBRARY_PATH | sed s+/usr/local/cuda/compat++)

echo "STARTING TORCHRUN | $(date)"
SECONDS=0
ret=0
if ! torchrun \
    --node_rank "${RANK}" \
    --rdzv_endpoint "${MASTER_ADDR}:${MASTER_PORT}" \
    $(echo "$config_json" | jq -r '. | to_entries | .[] | ("--" + .key + " " + (.value | tostring))' | sed "s/ true//");
then
    ret=1
    echo "TORCHRUN FAILED :/ (retcode=$ret)"
fi
echo "TORCHRUN FINISHED after $SECONDS seconds | $(date)"

exit $ret
