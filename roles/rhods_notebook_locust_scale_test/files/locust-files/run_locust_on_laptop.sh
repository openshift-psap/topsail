#! /bin/bash

set -o errexit
set -o pipefail
set -o nounset
set -o errtrace
#set -x

THIS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
BASE_DIR="$(realpath "$THIS_DIR")/../../../.."
source "$BASE_DIR/testing/ods/configure.sh"

LOCUST_COMMAND="rhods notebook_locust_scale_test"

_get_command_arg() {
    cd "$BASE_DIR"
    get_command_arg "$@"
}

export ODH_DASHBOARD_URL="https://$(oc get route -n redhat-ods-applications rhods-dashboard -ojsonpath={.spec.host})"
export TEST_USERS_USERNAME_PREFIX=$(_get_command_arg username_prefix $LOCUST_COMMAND)
export TEST_USERS_IDP_NAME=$(_get_command_arg idp_name $LOCUST_COMMAND)
export USER_INDEX_OFFSET=$(_get_command_arg user_index_offset $LOCUST_COMMAND)

export CREDS_FILE=$(_get_command_arg secret_properties_file $LOCUST_COMMAND)
export NOTEBOOK_IMAGE_NAME=$(_get_command_arg notebook_image_name $LOCUST_COMMAND)
export NOTEBOOK_SIZE_NAME=$(_get_command_arg notebook_size_name $LOCUST_COMMAND)


export LOCUST_USERS=$(_get_command_arg user_count $LOCUST_COMMAND)
export LOCUST_SPAWN_RATE=$(_get_command_arg spawn_rate $LOCUST_COMMAND)
export LOCUST_RUN_TIME=$(_get_command_arg run_time $LOCUST_COMMAND)
# or
#export LOCUST_ITERATIONS=1


export LOCUST_LOCUSTFILE=$THIS_DIR/locustfile.py

export REUSE_COOKIES=1

DEBUG_MODE=${DEBUG_MODE:-1}
export DEBUG_MODE

if [[ "$DEBUG_MODE" == 1 ]]; then
    echo "Debug!"
    exec python3 "$LOCUST_LOCUSTFILE"
else
    mkdir -p results
    rm results/* -f
    echo "Run!"
    locust --headless \
           --reset-stats \
           --csv results/api_scale_test \
           --csv-full-history \
           --html results/api_scale_test.html \
           --only-summary || true

    locust-reporter \
        -prefix results/api_scale_test \
        -failures=true \
        -outfile results/locust_reporter.html
fi
