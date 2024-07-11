#! /bin/bash

set -o errexit
set -o pipefail
set -o nounset
set -x

configure_s3() {
    export S3_HOST_BASE=minio.$MINIO_NAMESPACE.svc.cluster.local:9000
    export S3_HOST_BUCKET=$S3_HOST_BASE

    export S3_ACCESS_KEY=minio
    # S3_SECRET_KEY: set below
    export HOME=/tmp/s3cmd
    mkdir -p "$HOME"
    if [[ -f "${CREDS_FILE:-}" ]]; then
        # run this in a subshell to avoid printing the password in clear because of 'set -x'
        bash -ec 'source "'${CREDS_FILE}'"; export S3_SECRET_KEY=$user_password; cat /mnt/s3-config/s3cfg | envsubst > ~/.s3cfg'
    else
        # run this in a subshell to avoid printing the password in clear because of 'set -x'
        bash -ec "eval \$(yq e .TEST_USER.PASSWORD /mnt/ods-ci-test-variables/test-variables.yml | awk '{ print \"export S3_SECRET_KEY=\" \$1 }'); cat /mnt/s3-config/s3cfg | envsubst > ~/.s3cfg"
    fi
}

echo "Artifacts retention mode: $ARTIFACTS_COLLECTED"

retcode=0 # always exit 0, we'll decide later if this is a success or a failure

if [[ "$ARTIFACTS_COLLECTED" == "none" ]]; then
    exit $retcode
fi

set +x

echo "$(date) Waiting for '${ARTIFACT_DIR}/test.exit_code' to appear ..."

while ! [[ -f "${ARTIFACT_DIR}/test.exit_code" ]]; do
    sleep 15
done

echo "$(date) '${ARTIFACT_DIR}/test.exit_code' appeared."

set -x

test_failed=$(cat ${ARTIFACT_DIR}/test.exit_code)

delete_screenshots=0

if [[ "$ARTIFACTS_COLLECTED" == "no-screenshot"* ]]; then
    delete_screenshots=1

    SKIP_FAILED_USER_COUNT_THRESHOLD=100

    if [[ "$ARTIFACTS_COLLECTED" == no-screenshot-except-failed-and-zero && "$USER_COUNT" -gt "$SKIP_FAILED_USER_COUNT_THRESHOLD" ]]; then
        ARTIFACTS_COLLECTED=no-screenshot-except-zero
        echo "More than $SKIP_FAILED_USER_COUNT_THRESHOLD simulted users, cannot keep the failed artifacts. Switching to '$ARTIFACTS_COLLECTED'."
    fi

    # no-screenshot-except-zero or no-screenshot-except-failed-and-zero
    [[ "$ARTIFACTS_COLLECTED" == *"-zero" && "${JOB_COMPLETION_INDEX:-0}" == 0 ]] && delete_screenshots=0

    # no-screenshot-except-failed or no-screenshot-except-failed-and-zero
    [[ "$ARTIFACTS_COLLECTED" == *"-failed"* && "$test_failed" != 0 ]] && delete_screenshots=0
fi

if [[ "$delete_screenshots" == 1 ]]; then
    find "${ARTIFACT_DIR}" -name 'selenium-screenshot-*.png' -delete > dev/null
fi

configure_s3

find "${ARTIFACT_DIR}"

s3cmd put  --no-check-certificate \
      "${ARTIFACT_DIR}"/* \
      "s3://$S3_BUCKET_NAME/$BUCKET_DEST_DIR/$HOSTNAME/" \
      --recursive --no-preserve --no-progress --stats --quiet

exit $retcode
