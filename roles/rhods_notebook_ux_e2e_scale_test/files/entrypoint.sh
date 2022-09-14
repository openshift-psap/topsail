#! /bin/bash

set -o errexit
set -o pipefail
set -o nounset
set -x

JOB_COMPLETION_INDEX=${JOB_COMPLETION_INDEX:-0}
STATE_SIGNAL_BARRIER=/mnt/rhods-notebook-ux-e2e-scale-test-entrypoint/state-signal_barrier.py
STATE_SIGNAL_DELAY=120 # delay for all the Pods to reach the entry barrier

if [[ -z "{ARTIFACT_DIR:-}" ]]; then
    ARTIFACT_DIR=/tmp/ods-ci
fi

mkdir -p "${ARTIFACT_DIR}"

trap "touch $ARTIFACT_DIR/test.exit_code" EXIT

sed "s/#{JOB_COMPLETION_INDEX}/${JOB_COMPLETION_INDEX}/g" /mnt/ods-ci-test-variables/test-variables.yml > /tmp/test-variables.yml

cp "/mnt/rhods-notebook-ux-e2e-scale-test-entrypoint/$RUN_ROBOT_TEST_CASE" .

# Use StateSignal-barrier to wait for all the Pods to be ready

python3 -m pip --no-cache-dir install state-signals==0.5.2 --user
echo "Running with user $JOB_COMPLETION_INDEX / $USER_COUNT"
if [[ $JOB_COMPLETION_INDEX == 0 ]]; then
    python3 "$STATE_SIGNAL_BARRIER" "$REDIS_SERVER" --exporter "$USER_COUNT" --delay "$STATE_SIGNAL_DELAY" &
fi

date
time python3 "$STATE_SIGNAL_BARRIER" "$REDIS_SERVER" # fails if the all Pods don't reach the barrier in time
date
# Sleep for a while to avoid DDoSing OAuth

sleep_delay=$(python3 -c "print($JOB_COMPLETION_INDEX * $SLEEP_FACTOR)")

echo "Waiting $sleep_delay seconds before starting (job index: $JOB_COMPLETION_INDEX, sleep factor: $SLEEP_FACTOR)"
echo "$sleep_delay" > "${ARTIFACT_DIR}/sleep_delay"
sleep "$sleep_delay"
date

test_exit_code=0
(bash -x ./run_robot_test.sh \
    --skip-pip-install \
    --test-variables-file /tmp/test-variables.yml \
    --skip-oclogin true \
    --test-artifact-dir "$ARTIFACT_DIR" \
    --test-case "$RUN_ROBOT_TEST_CASE" \
    --exclude "$RUN_ROBOT_EXCLUDE_TAGS" \
    --extra-robot-args "--exitonfailure" \
    |& tee "${ARTIFACT_DIR}/test.log") || test_exit_code=$?

# /!\ the creation of this file triggers the export of the logs
echo "$test_exit_code" > "${ARTIFACT_DIR}/test.exit_code"

echo "Test finished with $test_exit_code errors."

exit 0 # always exit 0, we'll decide later if this is a success or a failure
