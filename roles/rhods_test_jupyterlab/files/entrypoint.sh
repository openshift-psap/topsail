#! /bin/bash

set -o errexit
set -o pipefail
set -o nounset
set -x

sed  "s/#{JOB_COMPLETION_INDEX}/${JOB_COMPLETION_INDEX}/g" /mnt/ods-ci-test-variables/test-variables.yml > /tmp/test-variables.yml

export KUBECONFIG=/tmp/kube

export K8S_API=$(yq e .OCP_API_URL /tmp/test-variables.yml)
export USERNAME=$(yq e .TEST_USER.USERNAME /tmp/test-variables.yml)

touch "$KUBECONFIG"
# run this in a subshell to avoid printing the password in clear because of 'set -x'
bash -ec "PASSWORD=\$(yq e .TEST_USER.PASSWORD /tmp/test-variables.yml); oc login --server=\$K8S_API --username=\$USERNAME --password=\$PASSWORD --insecure-skip-tls-verify"

if ./run_robot_test.sh \
    --skip-pip-install \
    --test-variables-file /tmp/test-variables.yml \
    --test-case "$TEST_CASE";
then
    FINISH=success
else
    FINISH=failure
fi

echo "$FINISH" > /tmp/finish

export S3_HOST_BASE=minio.minio.svc.cluster.local:9000
export S3_HOST_BUCKET=$S3_HOST_BASE

export S3_ACCESS_KEY=minio
# S3_SECRET_KEY: set below

# run this in a subshell to avoid printing the password in clear because of 'set -x'
bash -ec "eval \$(yq e .TEST_USER.PASSWORD /tmp/test-variables.yml | awk '{ print \"export S3_SECRET_KEY=\" \$1 }'); cat /mnt/s3-config/s3cfg | envsubst > ~/.s3cfg"

s3cmd put \
      /tmp/finish /tmp/ods-ci/test-output/*/* \
      s3://mybucket/ods-ci/$HOSTNAME/ \
      --recursive \
      --no-preserve \
      --no-progress \
      --stats

exit 0 # always exit 0, we'll decide later if this is a success or a failure
