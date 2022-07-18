#! /bin/bash

set -o pipefail
set -o errexit
set -o nounset
set -o errtrace
set -x

export PSAP_ODS_SECRET_PATH=/var/run/psap-ods-secret-1

export AWS_SHARED_CREDENTIALS_FILE="${PSAP_ODS_SECRET_PATH:-}/.awscred"

python3 ./subprojects/cloud-watch/cleanup-velero-buckets.py --delete
