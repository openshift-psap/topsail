# !/bin/bash

set -o pipefail
set -o errexit
set -o nounset
set -o errtrace
set -x

export SFT_TRAINER_CONFIG_JSON_PATH=$CONFIG_JSON_PATH

if [[ $WORLD_SIZE == 1 ]]; then
    echo "Running on a single machine."

    if [[ -z "${NUM_GPUS:-1}" || "${NUM_GPUS:-1}" == 1 ]]; then
        echo "Running with a single GPU"
    else
        echo "Running with a $NUM_GPUS GPUs"
    fi
    time python /app/accelerate_launch.py
    exit 0
fi
echo "Running on $WORLD_SIZE machines with $NUM_GPUS GPUs each."

time accelerate launch \
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
