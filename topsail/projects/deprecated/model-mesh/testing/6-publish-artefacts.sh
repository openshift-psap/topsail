#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset
set -o errtrace
set -x

results_dir=$ARTIFACT_DIR/results
mkdir -p "$results_dir"
touch $results_dir/settings
echo "0" > $results_dir/exit_code
mkdir -p $results_dir/artifacts-sutest
oc get nodes -oyaml > $results_dir/artifacts-sutest/nodes.yaml
mv $ARTIFACT_DIR/*__cluster__dump_prometheus_db/prometheus.tar.gz $results_dir/artifacts-sutest/prometheus_ocp.tgz
