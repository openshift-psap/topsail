#! /bin/bash

set -o errexit
set -o pipefail
set -o nounset
set -x

JOB_COMPLETION_INDEX=${JOB_COMPLETION_INDEX:-1}

if [[ -z "{ARTIFACTS_DIR:-}" ]]; then
    ARTIFACTS_DIR=/tmp/ods-ci
fi

mkdir -p "${ARTIFACTS_DIR}"

trap "touch $ARTIFACTS_DIR/test.exit_code" EXIT

sed "s/#{JOB_COMPLETION_INDEX}/${JOB_COMPLETION_INDEX}/g" /mnt/ods-ci-test-variables/test-variables.yml > /tmp/test-variables.yml

cp "/mnt/rhods-jupyterlab-entrypoint/$RUN_ROBOT_TEST_CASE" .

# Sleep for a while to avoid DDoSing OAuth

sleep_delay=$(python3 -c "print($JOB_COMPLETION_INDEX * $SLEEP_FACTOR)")

echo "Waiting $sleep_delay seconds before starting (job index: $JOB_COMPLETION_INDEX, sleep factor: $SLEEP_FACTOR)"
echo "$sleep_delay" > "${ARTIFACTS_DIR}/sleep_delay"
sleep "$sleep_delay"

test_exit_code=0
(bash -x ./run_robot_test.sh \
    --skip-pip-install \
    --test-variables-file /tmp/test-variables.yml \
    --skip-oclogin true \
    --test-artifact-dir "$ARTIFACTS_DIR" \
    --test-case "$RUN_ROBOT_TEST_CASE" \
    --exclude "$RUN_ROBOT_EXCLUDE_TAGS" \
    |& tee "${ARTIFACTS_DIR}/test.log") || test_exit_code=$?

# /!\ the creation of this file triggers the export of the logs
echo "$test_exit_code" > "${ARTIFACTS_DIR}/test.exit_code"

echo "Test finished with $test_exit_code errors."

exit 0 # always exit 0, we'll decide later if this is a success or a failure
