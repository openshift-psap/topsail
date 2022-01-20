#! /usr/bin/env bash

set -o errexit
set -o pipefail
set -o nounset

local_name="ssd"
tag="nvidiadl-ssd-training-benchmark"

repo="https://github.com/openshift-psap/training_results_v0.7.git"
path="NVIDIA/benchmarks/ssd/implementations/pytorch"
branch="fix/build-error" # Using a custom commit to avoid an existing image build bug
memory=5 # Gb
quay="openshift-psap/ci-artifacts"
auth="/var/run/psap-entitlement-secret/openshift-psap-openshift-ci-secret.yml"

./run_toolbox.py utils build_push_image $local_name $tag \
    --git_repo=$repo \
    --git_path=$path \
    --branch=$branch \
    --memory=$memory \
    --quay_org_repo=$quay \
    --auth_file=$auth
