#! /usr/bin/env bash

set -o errexit
set -o pipefail
set -o nounset
set -x

local_name="ssd"
tag="mlperf-ssd-training-benchmark"

repo="https://github.com/openshift-psap/training_results_v0.7.git"
ref="fix/build-error" # Using a custom commit to avoid an existing image build bug
context_dir="/NVIDIA/benchmarks/ssd/implementations/pytorch"
dockerfile_path="Dockerfile"

memory=5 # Gb

remote_repo="quay.io/openshift-psap/ci-artifacts"
auth="/var/run/psap-entitlement-secret/openshift-psap-openshift-ci-secret.yml"

./run_toolbox.py utils build_push_image "$local_name" "$tag" \
    --namespace=utils-ci \
    --git-repo="$repo" \
    --git-ref="$ref" \
    --context-dir="$context_dir" \
    --dockerfile-path="$dockerfile_path" \
    --remote-repo="$remote_repo" \
    --remote-auth-file="$auth" \
    --memory="$memory"
