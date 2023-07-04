#! /bin/bash

set -o pipefail
set -o errexit
set -o nounset
set -x

# Chosen as it's tested to terminate within the alloted time
SEED=5652442

EPOCHS=${BENCHMARKING_EPOCHS:-80}
echo "Using epochs=$EPOCHS"
THRESHOLD=${BENCHMARKING_THRESHOLD:-0.23}
echo "Using threshold=$THRESHOLD"

DATASET_DIR=/storage

if [ ! -f ${DATASET_DIR}/annotations/bbox_only_instances_train2017.json ]; then
    echo "Prepare instances_train2017.json ..."
    ./prepare-json.py \
        "${DATASET_DIR}/annotations/instances_train2017.json" \
        "${DATASET_DIR}/annotations/bbox_only_instances_train2017.json"
fi

if [ ! -f ${DATASET_DIR}/annotations/bbox_only_instances_val2017.json ]; then
    echo "Prepare instances_val2017.json ..."
    ./prepare-json.py --keep-keys \
        "${DATASET_DIR}/annotations/instances_val2017.json" \
        "${DATASET_DIR}/annotations/bbox_only_instances_val2017.json"
fi

export TORCH_HOME=${DATASET_DIR}/torchvision

ls /storage
ls -alF /storage/annotations
unset CUDA_VISIBLE_DEVICES

PYCMD=$(cat <<EOF
import pycuda
from pycuda import compiler
import pycuda.driver as drv

drv.init()
print("%d device(s) found." % drv.Device.count())
           
for ordinal in range(drv.Device.count()):
    dev = drv.Device(ordinal)
    print (ordinal, dev.name())
EOF
)

python -c "$PYCMD"

export NCCL_DEBUG=INFO
export CUDA_VISIBLE_DEVICES=0
time python -u -m bind_launch --nsockets_per_node=1 --ncores_per_socket=1 --nproc_per_node=1 \
     train.py --epochs ${EPOCHS} \
              --threshold=${THRESHOLD} \
              --data ${DATASET_DIR} \
              --no-save \
              --use-fp16 --nhwc \
              --evaluation 1 2 3 6 12 40 70 \
              --num-workers=1 \
              --batch-size=16 \
              --local_rank=0 \
              --warmup=1 \
              --warmup-factor 1 \
              --seed $SEED
