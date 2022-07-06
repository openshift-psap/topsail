#! /bin/bash

set -o errexit
set -o pipefail
set -o nounset
set -x

JOB_COMPLETION_INDEX=${JOB_COMPLETION_INDEX:-1}

do_oc_login() {
    export KUBECONFIG=/tmp/kube

    export K8S_API=$(yq e .OCP_API_URL /tmp/test-variables.yml)
    export USERNAME=$(yq e .TEST_USER.USERNAME /tmp/test-variables.yml)

    touch "$KUBECONFIG"
    retries=5
    tries=1
    while true; do
        # run this in a subshell to avoid printing the password in clear because of 'set -x'
        if bash -ec "PASSWORD=\$(yq e .TEST_USER.PASSWORD /tmp/test-variables.yml); oc login --server=\$K8S_API --username=\$USERNAME --password=\$PASSWORD --insecure-skip-tls-verify"; then
            echo "$tries"> "$ARTIFACTS_DIR/oc_login.tries"
            break
        fi
        tries=$(($tries + 1))
        retries=$(($retries - 1))
        [[ $retries == 0 ]] && return 1
        sleep 10
    done
}

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
sleep "$sleep_delay"

# This isn't necessary for the testing, Keep it until
# `run_robot_test.sh` initialization stops complaining when we provide
# no KUBECONFIG.
do_oc_login

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
