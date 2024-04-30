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

exec python launch_training.py
