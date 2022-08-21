#! /bin/bash

set -o pipefail
set -o errexit
set -o nounset
set -o errtrace
set -x

if [[ "${INSIDE_CI_IMAGE:-}" == "y" ]]; then
    export AWS_DEFAULT_PROFILE=${AWS_DEFAULT_PROFILE:-ci-artifact}
    export AWS_SHARED_CREDENTIALS_FILE="${PSAP_ODS_SECRET_PATH:-}/.awscred"
    export AWS_CONFIG_FILE=/tmp/awccfg

    cat <<EOF > $AWS_CONFIG_FILE
[$AWS_DEFAULT_PROFILE]
output=text
EOF
fi

exec python3 ./subprojects/cloud-watch/cleanup-velero-buckets.py --delete
