#! /bin/bash

set -o errexit
set -o pipefail
set -o nounset
set -x

S3_BUCKET_NAME=mybucket

configure_s3() {
    export S3_HOST_BASE=minio.minio.svc.cluster.local:9000
    export S3_HOST_BUCKET=$S3_HOST_BASE

    export S3_ACCESS_KEY=minio
    # S3_SECRET_KEY: set below

    # run this in a subshell to avoid printing the password in clear because of 'set -x'
    bash -ec "eval \$(yq e .TEST_USER.PASSWORD /mnt/ods-ci-test-variables/test-variables.yml | awk '{ print \"export S3_SECRET_KEY=\" \$1 }'); cat /mnt/s3-config/s3cfg | envsubst > ~/.s3cfg"
}

echo "Artifacts retention mode: $ARTIFACTS_COLLECTED"

retcode=0 # always exit 0, we'll decide later if this is a success or a failure

if [[ "$ARTIFACTS_COLLECTED" == "none" ]]; then
    exit $retcode
fi

dnf -y --quiet install https://dl.fedoraproject.org/pub/epel/epel-release-latest-8.noarch.rpm
dnf install -y --quiet s3cmd gettext
dnf clean all

curl --silent -L https://github.com/mikefarah/yq/releases/download/v4.25.1/yq_linux_amd64 -o /usr/bin/yq
chmod +x /usr/bin/yq

set +x

echo "$(date) Waiting for '${ARTIFACTS_DIR}/test.exit_code' to appear ..."

while ! [[ -f "${ARTIFACTS_DIR}/test.exit_code" ]]; do
    sleep 15
done

echo "$(date) '${ARTIFACTS_DIR}/test.exit_code' appeared."

set -x

test_failed=$(cat ${ARTIFACTS_DIR}/test.exit_code)

delete_image=0
[[ "$ARTIFACTS_COLLECTED" == "no-image" ]] && delete_image=1
[[ "$ARTIFACTS_COLLECTED" == "no-image-except-failed"* && "$test_failed" == 0 ]] && delete_image=1
[[ "$ARTIFACTS_COLLECTED" == "no-image-except-failed-and-zero" && "${JOB_COMPLETION_INDEX:-0}" == 0 ]] && delete_image=0

if [[ "$delete_image" == 1 ]]; then
    find "${ARTIFACTS_DIR}" -name '*.png' -delete > dev/null
fi

configure_s3

s3cmd put \
      "${ARTIFACTS_DIR}/test.exit_code" \
      "${ARTIFACTS_DIR}/test.log" \
      "${ARTIFACTS_DIR}"/ods-ci-*/* \
      "s3://$S3_BUCKET_NAME/ods-ci/$HOSTNAME/" \
      --recursive --no-preserve --no-progress --stats

exit $retcode
