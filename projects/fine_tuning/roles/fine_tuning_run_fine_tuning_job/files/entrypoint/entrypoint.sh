# !/bin/bash

set -o pipefail
set -o errexit
set -o nounset
set -o errtrace
set -x

echo "Source dataset: $DATASET_SOURCE"

if [[ "${DATASET_TRANSFORM:-}" ]]; then
    echo "Dataset transformation: $DATASET_TRANSFORM"

    python "$DATASET_TRANSFORM" "$DATASET_SOURCE" "$DATASET_DEST"
else
    cp "$DATASET_SOURCE" "$DATASET_DEST"
fi

if [[ "${DATASET_REPLICATION:-1}" != 1 ]]; then
    echo "Dataset replication factor: $DATASET_REPLICATION"
    python /mnt/entrypoint/convert_replicate.py "$DATASET_DEST" /tmp/temp_ds.json "$DATASET_REPLICATION"
    mv /tmp/temp_ds.json "$DATASET_DEST"
fi

echo "SFT-Trainer configuration:"
cat "$SFT_TRAINER_CONFIG_JSON_PATH"

if [[ -e /dev/nvidiactl ]]; then
    echo "# GPU available:"
    nvidia-smi -L
else
    echo "No GPU seem to be available."
fi

if [[ $WORLD_SIZE == 1 ]]; then
    echo "Running on a single machine."

    if [[ -z "${NUM_GPUS:-1}" || "${NUM_GPUS:-1}" == 1 ]]; then
        echo "Running with a single GPU"
        exec python launch_training.py
    else
        echo "Running with a $NUM_GPUS GPUs"
        exec  python /app/accelerate_launch.py
    fi
fi
echo "Running on $WORLD_SIZE machines with $NUM_GPUS GPUs each."

exec accelerate launch \
     --debug \
     --machine_rank $RANK \
     --num_machines $WORLD_SIZE \
     --num_processes $WORLD_SIZE \
     --main_process_ip $MASTER_ADDR \
     --main_process_port $MASTER_PORT \
     --mixed_precision no \
     --dynamo_backend no \
     --multi_gpu \
     launch_training.py
