# !/bin/bash

set -o pipefail
set -o errexit
set -o nounset
set -o errtrace
set -x

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

# --working-dir /mnt/ft-scripts/
ray job submit -- echo hello #bash -x /mnt/entrypoint/job_entrypoint.sh
