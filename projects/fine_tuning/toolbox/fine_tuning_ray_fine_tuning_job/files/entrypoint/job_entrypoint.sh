# !/bin/bash

set -o pipefail
set -o errexit
set -o nounset
set -o errtrace
set -x

# echo "Source dataset: $DATASET_SOURCE"

# MAX_SEQ_LENGTH=$(cat "$FT_CONFIG_JSON_PATH" | grep max_seq_length | awk '{print $2}' | cut -d"," -f1)
# DATASET_CACHE_FILE="/mnt/storage/dataset/$(basename "${DATASET_TRANSFORM:-}")_replicate_${DATASET_REPLICATION}_max${MAX_SEQ_LENGTH}tokens_$(basename "${DATASET_SOURCE}")"

# prepare_dataset() {
#     if [[ -f "${DATASET_CACHE_FILE:-}" ]]; then
#         echo "Found dataset cache file $DATASET_PREFER_CACHE. Not regenerating it."
#         return
#     fi

#     if [[ "${DATASET_TRANSFORM:-}" ]]; then
#         echo "Dataset transformation: $DATASET_TRANSFORM"

#         python "$DATASET_TRANSFORM" "$DATASET_SOURCE" "$DATASET_CACHE_FILE"
#     else
#         cp "$DATASET_SOURCE" "$DATASET_CACHE_FILE"
#     fi

#     if [[ "${DATASET_REPLICATION:-1}" != 1 ]]; then
#         echo "Dataset replication factor: $DATASET_REPLICATION"
#         python /mnt/entrypoint/convert_replicate.py "$DATASET_CACHE_FILE" /tmp/temp_ds.json "$DATASET_REPLICATION"
#         mv /tmp/temp_ds.json "$DATASET_CACHE_FILE"
#     fi
# }

# prepare_dataset

# echo "# sha256sum of the dataset files"
# sha256sum "$DATASET_SOURCE" "$DATASET_CACHE_FILE"

DATASET_FILE=/mnt/storage/dataset/ray-finetune-llm-deepspeed_train.jsonl
DATASET_TEST_FILE=/mnt/storage/dataset/ray-finetune-llm-deepspeed_test.jsonl

if [[ "${DATASET_PREPARE_CACHE_ONLY:-0}" == true ]]; then
    echo "DATASET_PREPARE_CACHE_ONLY is set, stopping here."
    exit 0
fi

echo "# configuration:"
cat "$FT_CONFIG_JSON_PATH"

echo "# sha256sum of the $MODEL_NAME files"
if [[ -f "/mnt/storage/model/${MODEL_NAME}.sha256sum" ]]; then
    cat "/mnt/storage/model/${MODEL_NAME}.sha256sum"
else
    time find "/mnt/storage/model/$MODEL_NAME" ! -path '*/.git/*' -type f -exec sha256sum {} \; | tee -a "/mnt/storage/model/${MODEL_NAME}.sha256sum"
fi

if [[ -e /dev/nvidiactl ]]; then
    echo "# GPU available:"
    nvidia-smi -L
else
    echo "No GPU seem to be available."
fi

cd /mnt/ft-scripts

if [[ "${SLEEP_FOREVER:-}" ]]; then
    set +x
    echo "Sleep flag enabled, sleeping forever."
    echo "Fine-tuning command:"
    cat <<EOF
oc rsh -n $(cat /run/secrets/kubernetes.io/serviceaccount/namespace) $(cat /proc/sys/kernel/hostname)
cp \$FT_CONFIG_JSON_PATH .
export FT_CONFIG_JSON_PATH=\$PWD/config.json
ray submit ...
EOF
    exec sleep inf
fi

find $PWD
find /mnt/output

DEST_DIR=/mnt/storage/generated
rm -rf "$DEST_DIR"
mkdir -p "$DEST_DIR"

if python ray_finetune_llm_deepspeed.py \
    --model-name="/mnt/storage/model/$MODEL_NAME" \
    --lora \
    --num-devices=8  \
    --num-epochs=5 \
    --ds-config=deepspeed_configs/zero_3_offload_optim_param.json \
    --batch-size-per-device=32 \
    --eval-batch-size-per-device=32 \
    "--train-path=$DATASET_FILE" \
    "--test-path=$DATASET_TEST_FILE" \
    "--dataset-config=${DATASET_FILE}.config.json" \
    "--storage-path=$DEST_DIR" \
    --ds-config=zero_3_offload_optim_param.json \
    --lora-config=lora.json;
then
    echo "SCRIPT SUCCEEDED"
else
    echo "SCRIPT FAILED"
    # don't exit with a return code != 0, otherwise the RayJob->Job retries 3 times ...
fi

find "$DEST_DIR" -type f
rm -r "$DEST_DIR"
