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

if [[ -n "${RETRIEVE:-}" ]] && [[ "$RANK" -eq 0 ]]; then
    # NOTE: Write here the code to copy any file you want to export to the test artifacts
    cp /etc/os-release "$RETRIEVE"
fi
