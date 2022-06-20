#! /bin/bash

set -o errexit
set -o pipefail
set -o nounset
set -x

sed "s/#{JOB_COMPLETION_INDEX}/${JOB_COMPLETION_INDEX}/g" /mnt/ods-ci-test-variables/test-variables.yml > /tmp/test-variables.yml

if [[ -z "{ARTIFACTS_DIR:-}" ]]; then
    ARTIFACTS_DIR=/tmp/ods-ci
fi

mkdir -p "${ARTIFACTS_DIR}"

trap "touch $ARTIFACTS_DIR/test_exit_code" EXIT

touch "$KUBECONFIG"
# run this in a subshell to avoid printing the password in clear because of 'set -x'
bash -ec "PASSWORD=\$(yq e .TEST_USER.PASSWORD /tmp/test-variables.yml); oc login --server=\$K8S_API --username=\$USERNAME --password=\$PASSWORD --insecure-skip-tls-verify"

test_exit_code=0
bash -x ./run_robot_test.sh \
    --skip-pip-install \
    --test-variables-file /tmp/test-variables.yml \
    --skip-oclogin true \
    --test-artifact-dir "$ARTIFACTS_DIR" \
    --test-case "$TEST_CASE" \
    || test_exit_code=$?

# /!\ the creation of this file triggers the export of the logs
echo "$test_exit_code" > "${ARTIFACTS_DIR}/test_exit_code"

echo "Test finished with $test_exit_code errors."

exit 0 # always exit 0, we'll decide later if this is a success or a failure
