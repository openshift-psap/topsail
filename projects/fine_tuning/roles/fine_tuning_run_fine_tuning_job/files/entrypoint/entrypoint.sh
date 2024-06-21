# !/bin/bash

set -o pipefail
set -o errexit
set -o nounset
set -o errtrace
set -x

echo "Transformer version"
pip freeze | grep transformers

echo "Source dataset: $DATASET_SOURCE"

prepare_dataset() {
    if [[ -f "${DATASET_PREFER_CACHE:-}" ]]; then
        echo "Found dataset cache file $DATASET_PREFER_CACHE. Not regenerating it."
        cp "$DATASET_PREFER_CACHE" "$DATASET_DEST"
        return
    fi

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

    if [[ -n "${DATASET_PREFER_CACHE:-}" ]]; then
        echo "Saving dataset cache into $DATASET_PREFER_CACHE"
        cp "$DATASET_DEST" "$DATASET_PREFER_CACHE"
    fi
}

prepare_dataset

if [[ "${DATASET_PREPARE_CACHE_ONLY:-0}" == true ]]; then
    echo "DATASET_PREPARE_CACHE_ONLY is set, stopping here."
    exit 0
fi

echo "SFT-Trainer configuration:"
cat "$SFT_TRAINER_CONFIG_JSON_PATH"

if [[ -e /dev/nvidiactl ]]; then
    echo "# GPU available:"
    nvidia-smi -L
else
    echo "No GPU seem to be available."
fi

if [[ "${SLEEP_FOREVER:-}" ]]; then
    set +x
    echo "Sleep flag enabled, sleeping forever."
    echo "Fine-tuning command:"
    cat <<EOF
oc rsh -n $(cat /run/secrets/kubernetes.io/serviceaccount/namespace) $(cat /proc/sys/kernel/hostname)
cp \$SFT_TRAINER_CONFIG_JSON_PATH .
export SFT_TRAINER_CONFIG_JSON_PATH=\$PWD/config.json
python /app/accelerate_launch.py
EOF
    exec sleep inf
fi

if [[ $WORLD_SIZE == 1 ]]; then
    echo "Running on a single machine."

    if [[ -z "${NUM_GPUS:-1}" || "${NUM_GPUS:-1}" == 1 ]]; then
        echo "Running with a single GPU"
    else
        echo "Running with a $NUM_GPUS GPUs"
    fi
    exec python /app/accelerate_launch.py
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
