#! /bin/bash

ls /storage
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
