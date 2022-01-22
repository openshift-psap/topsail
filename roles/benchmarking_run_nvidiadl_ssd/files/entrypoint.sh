#! /bin/bash

ls /storage

exec python -u -m bind_launch --nsockets_per_node=1 --ncores_per_socket=4 --nproc_per_node=4 \
     train.py --epochs 2 \
              --warmup-factor 0 \
              --threshold=0.25 \
              --data /storage \
              --batch-size=32 \
              --warmup=1
