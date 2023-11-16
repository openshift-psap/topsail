#! /bin/bash

set -o errexit
set -o pipefail
set -o nounset
set -o errtrace
#set -x

THIS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
BASE_DIR="$(realpath "$THIS_DIR")/../../../.."
source "$BASE_DIR/projects/notebooks/testing/configure.sh"

LOCUST_COMMAND="notebooks locust_scale_test"

_get_command_arg() {
    cd "$BASE_DIR"
    get_command_arg "$@"
}

export ODH_DASHBOARD_URL="https://$(oc get route -n redhat-ods-applications rhods-dashboard -ojsonpath={.spec.host})"
export TEST_USERS_USERNAME_PREFIX=$(_get_command_arg username_prefix $LOCUST_COMMAND)
export TEST_USERS_IDP_NAME=$(_get_command_arg idp_name $LOCUST_COMMAND)
export USER_INDEX_OFFSET=100

export CREDS_FILE=$(_get_command_arg secret_properties_file $LOCUST_COMMAND)
export NOTEBOOK_IMAGE_NAME=$(_get_command_arg notebook_image_name $LOCUST_COMMAND)
export NOTEBOOK_SIZE_NAME=$(_get_command_arg notebook_size_name $LOCUST_COMMAND)
export USER_SLEEP_FACTOR=$(_get_command_arg user_sleep_factor $LOCUST_COMMAND)

export LOCUST_USERS=$(_get_command_arg user_count $LOCUST_COMMAND)
#export LOCUST_RUN_TIME=$(_get_command_arg run_time $LOCUST_COMMAND)
export LOCUST_SPAWN_RATE=$LOCUST_USERS # Spawn all the users at the same time

echo "LOCUST_USERS --> $LOCUST_USERS"

export LOCUST_LOCUSTFILE=$THIS_DIR/locustfile.py
export RESULTS_DEST=results/locust_scale_test
export REUSE_COOKIES=1

export SKIP_OPTIONAL=${SKIP_OPTIONAL:-0}

DEBUG_MODE=${DEBUG_MODE:-0}
export DEBUG_MODE

if [[ "$DEBUG_MODE" == 1 ]]; then
    echo "Debug!"
    exec python3 "$LOCUST_LOCUSTFILE"
fi

unset LOCUST_RUN_TIME
mkdir -p results
rm results/* -f
echo "Run!"


export WORKER_COUNT=$(get_config tests.notebooks.locust.cpu_count)
# distributed locust options
export LOCUST_EXPECT_WORKERS=${WORKER_COUNT}
export LOCUST_EXPECT_WORKERS_MAX_WAIT=60 # seconds

export LOCUST_HEADLESS=1
export LOCUST_CSV=$RESULTS_DEST
export LOCUST_HTML=$LOCUST_CSV.html
export LOCUST_ONLY_SUMMARY=1
export LOCUST_ITERATIONS=$LOCUST_USERS # run only one iteration per user at the moment

unset process_ctrl__wait_list
declare -A process_ctrl__wait_list

locust --master &
MASTER_PID=$!

finish() {
    trap - INT
    echo "Killing the background processes still running ..."
    for pid in ${!process_ctrl__wait_list[@]}; do
        echo "- ${process_ctrl__wait_list[$pid]} (pid=$pid)"
        kill -KILL $pid 2>/dev/null || true
        unset process_ctrl__wait_list[$pid]
    done
    echo "All the processes have been terminated."

    kill -KILL $MASTER_PID
    echo "Waiting ..."
    wait $MASTER_PID

    locust-reporter \
        -prefix "$LOCUST_CSV" \
        -failures=true \
        -outfile "${RESULTS_DEST}_reporter.html"
}

trap finish INT

unset LOCUST_CSV
unset LOCUST_ONLY_SUMMARY
unset LOCUST_HTML
unset LOCUST_RUN_TIME
unset LOCUST_ITERATIONS

sleep 1 # give 1s for the locust coordinator to be ready
for worker in $(seq 1 ${WORKER_COUNT})
do
    sleep 0.1
    locust --worker &
    pid=$!
    process_ctrl__wait_list[$pid]="locust --worker"
done

wait $MASTER_PID
