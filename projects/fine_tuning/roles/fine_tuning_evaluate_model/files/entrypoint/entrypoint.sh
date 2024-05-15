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

if [[ -z "${NUM_GPUS:-1}" || "${NUM_GPUS:-1}" == 1 ]]; then
	echo "Running with a single process"
	exec python launch_training.py
fi

echo "Running with $NUM_GPUS GPUs"
echo "Running evaluation script"
echo "model=$MODEL_PATH"
echo "data_path=$DATASET_DEST"
exec python /tmp/fms-hf-tuning/scripts/run_evaluation.py --model $MODEL_PATH
