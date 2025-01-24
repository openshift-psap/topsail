# !/bin/bash

set -o pipefail
set -o errexit
set -o nounset
set -o errtrace
set -x

export SFT_TRAINER_CONFIG_JSON_PATH=$CONFIG_JSON_PATH

RETRIEVE_FILES=()

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

time python /app/accelerate_launch.py

if [[ -n "${RETRIEVE:-}" ]] && [[ "$RANK" -eq 0 ]] && [[ -n "${RETRIEVE_FILES:-}" ]]; then
    for file in "${RETRIEVE_FILES[@]}"; do
        if [[ -f "$file" ]]; then
            if cp "$file" "/mnt/storage/output/"; then
                echo "File $file copied to output directory"
            else
                echo "Failed to copy $file" >&2
            fi
        else
            echo "File $file not found" >&2
        fi
    done
fi
