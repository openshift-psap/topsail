#! /bin/bash

set -o errexit
set -o pipefail
set -o nounset
set -x

cd /tmp/ods-ci/ods_ci

JOB_COMPLETION_INDEX=${JOB_COMPLETION_INDEX:-0}
STATE_SIGNAL_BARRIER=/mnt/rhods-notebook-ux-e2e-scale-test-entrypoint/state-signal_barrier.py
STATE_SIGNAL_DELAY=-1 # delay for all the Pods to reach the entry barrier

if [[ -z "{ARTIFACT_DIR:-}" ]]; then
    ARTIFACT_DIR=/tmp/ods-ci
fi

mkdir -p "${ARTIFACT_DIR}"

trap "touch $ARTIFACT_DIR/test.exit_code" EXIT

echo "pod_starting: $(date)" > "${ARTIFACT_DIR}/progress_ts.yaml"

USER_INDEX=$(($USER_INDEX_OFFSET + $JOB_COMPLETION_INDEX))

sed "s/#{USER_INDEX}/${USER_INDEX}/g" /mnt/ods-ci-test-variables/test-variables.yml > /tmp/test-variables.yml

cp /mnt/rhods-notebook-ux-e2e-scale-test-entrypoint/* .

if [[ "$DRIVER_RUNNING_ON_SPOT_INSTANCES" == "False" ]]; then
    # workaround: HOME=/tmp isn't a writeable directory

    export HOME=/tmp/ods-ci # move to a writable HOME

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
else
    # Wait 60s after the Pod creation as an estimation for all the Pods to be ready
    echo "spotdelaysync_ready_to_wait: $(date)" >> "${ARTIFACT_DIR}/progress_ts.yaml"

    if [[ "$JOB_CREATION_TIME" == '$JOB_CREATION_TIME' ]]; then
        echo 'ERROR: driver running on spot instance but $JOB_CREATION_TIME is not set. Cannot continue.'
        # mark this test as failed
        echo 1 > "$ARTIFACT_DIR/test.exit_code"

        exit 0
    fi

    SPOT_START_DELAY=60 # in seconds
    cat >> /tmp/sync.py <<EOF
import datetime, time
job_creation_time = "$JOB_CREATION_TIME"
timedelta_seconds = $SPOT_START_DELAY
ready_time = datetime.datetime.strptime(job_creation_time, "%Y-%m-%dT%H:%M:%SZ") + datetime.timedelta(seconds=$SPOT_START_DELAY)
print("INFO: Hardcoded start delay:", timedelta_seconds, "seconds")
print("INFO: Job creation time:", job_creation_time)
print("INFO: Ready time:", ready_time)
print("INFO: Current time:", datetime.datetime.now())
print("INFO: Waiting time:", (ready_time - datetime.datetime.now()).total_seconds())
while datetime.datetime.now() < ready_time: time.sleep(1)
print("INFO: Done :)")
print("INFO: Current time:", datetime.datetime.now())
EOF
    time python3 /tmp/sync.py
    echo "spotdelaysync_ready: $(date)" >> "${ARTIFACT_DIR}/progress_ts.yaml"
fi

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
    --exclude "$RUN_ROBOT_EXCLUDE_TAGS" \
    --extra-robot-args "--exitonfailure" \
    |& tee "${ARTIFACT_DIR}/test.log") || test_exit_code=$?

mv "$ARTIFACT_DIR"/ods-ci-*/* "$ARTIFACT_DIR" || true

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
