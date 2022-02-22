#! /bin/bash

set -e
set -u
set -o pipefail
set -x

THIS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd ${THIS_DIR}

mode=${1:-}

if [[ -z "$mode" ]]; then
    echo "Please pass a mode as parameter"
    exit 1
fi

if [[ ! -f "./$mode/run.sh" ]]; then
    echo "Invalid mode: $mode"
    exit 1
fi

ENTITLEMENT_SECRET_PATH=/var/run/psap-entitlement-secret
export ENTITLEMENT_PEM=${ENTITLEMENT_PEM:-${ENTITLEMENT_SECRET_PATH}/entitlement.pem}

exec bash ./$mode/run.sh
