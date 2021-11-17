#!/bin/sh

if ! [[ -d  $ARTIFACT_DIR ]] ; then
    echo "FATAL: osde2e tests requires '/test-run-results' to exist"
    exit 1
fi

BURN_RUNTIME_SEC=600

function exit_and_abort() {
    echo "Failed. Aborting."
    exit 1
}


echo "====== Starting OSDE2E tests..."

echo "Using ARTIFACT_DIR=$ARTIFACT_DIR."

echo "====== waiting for gpu-operator..."

./run_toolbox.py gpu_operator wait_deployment || exit_and_abort
echo "====== Operator found."

echo "====== Running burn test for $((BURN_RUNTIME_SEC/60)) minutes ..."
./run_toolbox.py gpu_operator run_gpu_burn --runtime=${BURN_RUNTIME_SEC} || exit_and_abort
echo "====== Done."


