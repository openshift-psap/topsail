#!/bin/bash

set -o pipefail
set -o errexit
set -o nounset

set -x

cp /gpu-burn-src/* .

make

echo ""
echo "Running GPU Burn for ${GPU_BURN_TIME} seconds."
time ./gpu_burn $GPU_BURN_TIME
