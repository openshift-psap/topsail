#! /usr/bin/env bash

local_name="ssd"
tag="latest"

repo="https://github.com/openshift-psap/training_results_v0.7.git"
path="/NVIDIA/benchmarks/ssd/implementations/pytorch"
quay="openshift-psap/nvidiadl-ssd-training-benchmark"
auth="/var/run/psap-entitlement-secret/openshift-psap-openshift-ci-secret.yml"

./run_toolbox.py gpu_operator build_push_image $local_name $tag \
    --git_repo=$repo \
    --git_path=$path \
    --quay_org_repo=$quay \
    --auth_file=$auth
