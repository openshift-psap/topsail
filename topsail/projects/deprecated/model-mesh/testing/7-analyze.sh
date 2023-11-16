#!/bin/bash

set -o nounset
set -x

results_dir=$ARTIFACT_DIR/results
oc get nodes -oyaml > $results_dir/artifacts-sutest/nodes.yaml
oc get pods -A -owide | grep modelmesh > $results_dir/artifacts-sutest/pods.status
oc get inferenceservices -A > $results_dir/artifacts-sutest/inferenceservices.status
oc get servingruntimes -A > $results_dir/servingruntimes.status

BASE_ARTIFACT_DIR="$ARTIFACT_DIR"
PLOT_ARTIFACT_DIR="$ARTIFACT_DIR/plotting"
mkdir "$PLOT_ARTIFACT_DIR"
cp /logs/artifacts/variable_overrides "$PLOT_ARTIFACT_DIR"
if ARTIFACT_DIR="$PLOT_ARTIFACT_DIR" \
               ./testing/notebooks/generate_matrix-benchmarking.sh \
               from_dir "$BASE_ARTIFACT_DIR" \
                   > "$PLOT_ARTIFACT_DIR/build-log.txt" 2>&1;
then
    echo "INFO: MatrixBenchmarkings plots successfully generated."
else
    errcode=$?
    echo "ERROR: MatrixBenchmarkings plots generated failed. See logs in \$ARTIFACT_DIR/plotting/build-log.txt"
    exit $errcode
fi
