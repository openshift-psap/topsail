#! /bin/bash

set -o errexit
set -o pipefail
set -o nounset
set -x

sed  "s/#{JOB_COMPLETION_INDEX}/${JOB_COMPLETION_INDEX}/g" /mnt/ods-ci-test-variables/test-variables.yml > /tmp/test-variables.yml

echo "Artifacts retention mode: $ARTIFACTS_COLLECTED"

configure_s3() {
    export S3_HOST_BASE=minio.minio.svc.cluster.local:9000
    export S3_HOST_BUCKET=$S3_HOST_BASE

    export S3_ACCESS_KEY=minio
    # S3_SECRET_KEY: set below

    # run this in a subshell to avoid printing the password in clear because of 'set -x'
    bash -ec "eval \$(yq e .TEST_USER.PASSWORD /tmp/test-variables.yml | awk '{ print \"export S3_SECRET_KEY=\" \$1 }'); cat /mnt/s3-config/s3cfg | envsubst > ~/.s3cfg"

    date > /tmp/started

    s3cmd put /tmp/started \
          s3://mybucket/ods-ci/$HOSTNAME/ \
          --no-preserve \
          --no-progress
}

export KUBECONFIG=/tmp/kube

export K8S_API=$(yq e .OCP_API_URL /tmp/test-variables.yml)
export USERNAME=$(yq e .TEST_USER.USERNAME /tmp/test-variables.yml)

configure_s3

touch "$KUBECONFIG"
# run this in a subshell to avoid printing the password in clear because of 'set -x'
bash -ec "PASSWORD=\$(yq e .TEST_USER.PASSWORD /tmp/test-variables.yml); oc login --server=\$K8S_API --username=\$USERNAME --password=\$PASSWORD --insecure-skip-tls-verify"

test_exit_code=0
bash -x ./run_robot_test.sh \
    --skip-pip-install \
    --test-variables-file /tmp/test-variables.yml \
    --skip-oclogin true \
    --test-case "$TEST_CASE" \
    || test_exit_code=$?

echo "$test_exit_code" > /tmp/test_exit_code

echo "Test finished with $test_exit_code errors."

retcode=0 # always exit 0, we'll decide later if this is a success or a failure

if [[ "$ARTIFACTS_COLLECTED" == "none" ]]; then
    exit $retcode
fi

if [[ "$ARTIFACTS_COLLECTED" == "no-image" ]]; then
    find /tmp/ods-ci/test-output -name '*.png' -delete
fi

s3cmd put \
      /tmp/test_edit_code /tmp/ods-ci/test-output/*/* \
      s3://mybucket/ods-ci/$HOSTNAME/ \
      --recursive \
      --no-preserve \
      --no-progress \
      --stats

exit $retcode
