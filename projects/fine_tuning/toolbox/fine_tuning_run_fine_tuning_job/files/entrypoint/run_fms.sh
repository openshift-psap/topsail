# !/bin/bash

set -o pipefail
set -o errexit
set -o nounset
set -o errtrace
set -x

export SFT_TRAINER_CONFIG_JSON_PATH=$CONFIG_JSON_PATH

if [[ $WORLD_SIZE != 1 ]]; then
    echo "Running with a multi-node configuration. This is not supported at the moment, aborting."
    exit 1
fi

echo "Running on a single machine."

if [[ -z "${NUM_GPUS:-1}" || "${NUM_GPUS:-1}" == 1 ]]; then
    echo "Running with a single GPU"
else
    echo "Running with a $NUM_GPUS GPUs"
fi

export LOG_LEVEL=DEBUG

python -m accelerate.commands.launch \
  --num_processes=8 \
  --config-file /app/accelerate_fsdp_defaults.yaml \
  --dynamo_backend="no" \
  -m tuning.sft_trainer

python -m torch.distributed.run \
  --nproc_per_node=$NUM_GPUS \
  --nnodes=$WORLD_SIZE \
  --node_rank=$RANK \
  --master_addr=$MASTER_ADDR \
  --master_port=$MASTER_PORT \
  --module tuning.sft_trainer \
  --fsdp_auto_wrap_policy=TRANSFORMER_BASED_WRAP \
  --fsdp_backward_prefetch=BACKWARD_PRE \
  --fsdp_forward_prefetch=False \
  --fsdp_offload_params=False \
  --fsdp_state_dict_type=FULL_STATE_DICT \
  --fsdp_sync_module_states=True \
  --fsdp_use_orig_params=False \
  --fsdp_backward_prefetch_policy=BACKWARD_PRE \
  --fsdp_sharding_strategy=1 \
  --fsdp_cpu_ram_efficient_loading=True \
  --fsdp_sync_module_states=True

if [[ -n "${RETRIEVE:-}" ]] && [[ "$RANK" -eq 0 ]]; then
    # NOTE: Write here the code to copy any file you want to export to the test artifacts
    cp /etc/os-release "$RETRIEVE"
fi
