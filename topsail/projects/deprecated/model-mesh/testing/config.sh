#!/bin/bash

# Entrypoint configuration
SCALE_INSTANCES=0  # 0 for yes, 1 for no
# INSTANCE_TYPE="m6a.2xlarge"
INSTANCE_TYPE="m5.2xlarge"
INSTANCE_COUNT="2"
RUN_TIMEOUT="100m"
COLLECT_TIMEOUT="5m"
EXEC_LIST="1-install-mm.sh 2-serve-minio.sh 3-clear-prom-db.sh 4-deploy-many-ns-many-models.sh"
COLLECT_LIST="5-dump-and-clear-prom-db.sh 6-publish-artefacts.sh 7-analyze.sh"

# ModelMesh deployment related variables
MODELMESH_PROJECT="opendatahub"
INFERENCE_SERVICE_PROJECT="mesh-test"
KFCTL_RELEASE_URL="https://github.com/kubeflow/kfctl/releases/download/v1.2.0/kfctl_v1.2.0-0-gbc038f9_linux.tar.gz"
KFCTL_TARBALL="kfctl.tar.gz"

# MinIO Config
MINIO_NS="minio"
MODEL_PATH="/data1/modelmesh-example-models/onnx/"
MINIO_MODEL_COUNT=5

# Model Mesh deployment config
NS_COUNT=2
MODEL_COUNT=${MINIO_MODEL_COUNT}
NS_BASENAME=mm

# Smoke test config
API_ENDPOINT_CHECK=0 # 0 for yes, 1 for no
MM_POD_COUNT=2

# Plot
export MATBENCH_WORKLOAD=rhods-notebooks
CURL_OPTIONS="--silent --location --fail --show-error --insecure"
