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
  --dynamo_backend="no" \
  --fsdp_auto_wrap_policy="TRANSFORMER_BASED_WRAP" \
  --fsdp_cpu_ram_efficient_loading="true" \
  --fsdp_forward_prefetch="false" \
  --fsdp_offload_params="false" \
  --fsdp_sharding_strategy="HYBRID_SHARD" \
  --fsdp_state_dict_type="FULL_STATE_DICT" \
  --fsdp_sync_module_states="true" \
  --machine_rank="0" \
  --main_process_ip="127.0.0.1" \
  --main_process_port="29500" \
  --mixed_precision="no" \
  --num_machines="1" \
  --rdzv_backend="static" \
  --same_network \
  --use_fsdp \
  -m tuning.sft_trainer

if [[ -n "${RETRIEVE:-}" ]] && [[ "$RANK" -eq 0 ]]; then
    # NOTE: Write here the code to copy any file you want to export to the test artifacts
    cp /etc/os-release "$RETRIEVE"
fi
