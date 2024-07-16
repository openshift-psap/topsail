#! /bin/bash

set -o errexit
set -o pipefail
set -o nounset
set -x

cd /tmp/ods-ci/ods_ci

JOB_COMPLETION_INDEX=${JOB_COMPLETION_INDEX:-0}
STATE_SIGNAL_BARRIER=/mnt/dashboard-scale-test-entrypoint/state-signal_barrier.py
STATE_SIGNAL_DELAY=-1 # delay for all the Pods to reach the entry barrier

if [[ -z "{ARTIFACT_DIR:-}" ]]; then
    ARTIFACT_DIR=/tmp/ods-ci
fi

mkdir -p "${ARTIFACT_DIR}"

trap "touch $ARTIFACT_DIR/test.exit_code" EXIT

echo "pod_starting: $(date)" > "${ARTIFACT_DIR}/progress_ts.yaml"

USER_INDEX=$(($USER_INDEX_OFFSET + $JOB_COMPLETION_INDEX))

sed "s/#{USER_INDEX}/${USER_INDEX}/g" /mnt/ods-ci-test-variables/test-variables.yml > /tmp/test-variables.yml

cp /mnt/dashboard-scale-test-entrypoint/* .

# Workaround: /tmp is readonly, HOME isn't

export HOME=/tmp/ods-ci/ods_ci
export TMPDIR=$HOME/tmp

mkdir "$TMPDIR"

# Use StateSignal-barrier to wait for all the Pods to be ready
python3 -m ensurepip --user
python3 -m pip --no-cache-dir install state-signals==0.5.2 --user

echo "Running with user $JOB_COMPLETION_INDEX / $USER_COUNT"
if [[ $JOB_COMPLETION_INDEX == 0 ]]; then
    python3 "$STATE_SIGNAL_BARRIER" "$REDIS_SERVER" --exporter "$USER_COUNT" --delay "$STATE_SIGNAL_DELAY" &
fi

echo "statesignal_setup: $(date)" >> "${ARTIFACT_DIR}/progress_ts.yaml"
if ! python3 "$STATE_SIGNAL_BARRIER" "$REDIS_SERVER"; then # fails if the all Pods don't reach the barrier in time
    echo "StateSignal syncrhonization failed :( (errcode=$?)"

    # mark this test as failed
    echo 1 > "$ARTIFACT_DIR/test.exit_code"

    # exit the Pod successfully, so that all the Pod logs are retrieved.
    # without this, we don't know why the 'fail' event was generated.
    exit 0
fi
echo "statesignal_ready: $(date)" >> "${ARTIFACT_DIR}/progress_ts.yaml"

# end of the workaround: HOME=/tmp isn't a writeable directory
export HOME=/tmp # move back to the default HOME

# Sleep for a while to avoid DDoSing OAuth

sleep_delay=$(python3 -c "print(int($JOB_COMPLETION_INDEX / $USER_BATCH_SIZE) * $SLEEP_FACTOR)")

echo "Waiting $sleep_delay seconds before starting (job index: $JOB_COMPLETION_INDEX, sleep factor: $SLEEP_FACTOR)"

sleep "$sleep_delay"
echo "launch_delay: $(date)" >> "${ARTIFACT_DIR}/progress_ts.yaml"

test_exit_code=0
(bash -x ./run_robot_test.sh \
    --skip-install \
    --test-variables-file /tmp/test-variables.yml \
    --skip-oclogin true \
    --test-artifact-dir "$ARTIFACT_DIR" \
    --test-case "$RUN_ROBOT_TEST_CASE" \
    --extra-robot-args "--exitonfailure" \
    |& tee "${ARTIFACT_DIR}/test.log") || test_exit_code=$?

mv /tmp/ods-ci/ods_ci/tmp/ods-ci* "$ARTIFACT_DIR" || true

if [[ "$test_exit_code" != 0 && "$USER_COUNT" -gt 100 && "$JOB_COMPLETION_INDEX" != 0 ]]; then
    # test failed
    # and user count > 100
    # and user id != 0
    # --> delete all the images but the last (sorted by natural number order)
    for f in $(ls "$ARTIFACT_DIR"/selenium-screenshot -v1 | head -n -1); do
        rm -f "$f"
    done
fi

# /!\ the creation of this file triggers the export of the logs
echo "$test_exit_code" > "${ARTIFACT_DIR}/test.exit_code"

echo "Test finished with $test_exit_code errors."
echo "test_execution: $(date)" >> "${ARTIFACT_DIR}/progress_ts.yaml"

exit 0 # always exit 0, we'll decide later if this is a success or a failure