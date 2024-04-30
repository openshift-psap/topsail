# !/bin/bash

set -o pipefail
set -o errexit
set -o nounset
set -o errtrace
set -x

#python /mnt/entrypoint/convert_alpaca.py /data/dataset/alpaca_data.json
cat $SFT_TRAINER_CONFIG_JSON_PATH

if [[ -e /dev/nvidiactl ]]; then
    nvidia-smi -L
else
    echo "No GPU seem to be available."
fi

if [[ "${DATASET_TRANSFORM:-}" ]]; then
    python "$DATASET_TRANSFORM" "$DATASET_SOURCE" "$DATASET_DEST"
else
    cp "$DATASET_SOURCE" "$DATASET_DEST"
fi

if [[ "${DATASET_REPLICATION:-1}" != 1 ]]; then
    python /mnt/entrypoint/convert_replicate.py "$DATASET_DEST" /tmp/temp_ds.json "$DATASET_REPLICATION"
    mv /tmp/temp_ds.json "$DATASET_DEST"
fi

if [[ -z "${NUM_GPUS:-1}" || "${NUM_GPUS:-1}" == 1 ]]; then
    exec python launch_training.py
fi

exec python /app/accelerate_launch.py
