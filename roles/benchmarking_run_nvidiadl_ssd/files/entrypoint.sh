#! /bin/bash

ls /storage

exec python -m torch.distributed.launch --nproc_per_node=1 \
        main.py --batch-size 32 \
          --mode benchmark-training \
          --benchmark-warmup 100 \
          --benchmark-iterations 100 \
          --data /storage
