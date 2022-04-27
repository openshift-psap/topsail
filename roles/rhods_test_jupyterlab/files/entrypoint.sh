#! /bin/bash

set -o errexit
set -o pipefail
set -o nounset
set -x

sed  "s/#{JOB_COMPLETION_INDEX}/${JOB_COMPLETION_INDEX}/g" /mnt/ods-ci-test-variables/test-variables.yml > /tmp/test-variables.yml

FAKE=0
if [[ $FAKE == 1 ]]; then
    DEST="/tmp/ods-ci/test-output/ods-ci-$(date +"%Y-%M-%H_%T.%N")"
    mkdir -p "$DEST"
    touch "$DEST/FAKE_MODE"
    echo "world" > "$DEST/hello"
    FINISH=fake_mode
else
    ./run_robot_test.sh \
        --skip-pip-install \
        --test-variables-file /tmp/test-variables.yml \
        --test-case "$TEST_CASE" && FINISH=success || FINISH=failure
fi
echo "$FINISH" /tmp/finish

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

# always exit 0, we'll decide later if this is a success or a failure

exit 0
