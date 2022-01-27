#! /bin/bash

DATASET_DIR=/storage
if [ ! -f ${DATASET_DIR}/annotations/bbox_only_instances_train2017.json ]; then
    echo "Prepare instances_train2017.json ..."
    ./prepare-json.py \
        "${DATASET_DIR}/annotations/instances_train2017.json" \
        "${DATASET_DIR}/annotations/bbox_only_instances_train2017.json"
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
exec python -u -m bind_launch --nsockets_per_node=1 --ncores_per_socket=1 --nproc_per_node=1 \
     train.py --epochs 2 \
              --warmup-factor 0 \
              --threshold=0.25 \
              --data /storage \
              --batch-size=32 \
              --warmup=1 \
              --local_rank=0
