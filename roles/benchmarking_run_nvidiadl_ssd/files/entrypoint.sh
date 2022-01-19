#! /bin/bash

ls /storage

exec python -u -m bind_launch --nproc_per_node=1 \
     train.py --epochs 80 \
              --warmup-factor 0 \
              --threshold=0.23 \
              --data /storage \
              --batch-size=32 \
              --warmup=100
