#! /bin/bash

set -o pipefail
set -o errexit
set -o nounset
set -o errtrace
set -x

TESTING_ODS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

source "$TESTING_ODS_DIR/../_logging.sh"
source "$TESTING_ODS_DIR/configure.sh"

if [[ "${IGNORE_PSAP_ODS_SECRET_PATH:-0}" == 1 ]]; then
    _info "Ignoring the check of PSAP_ODS_SECRET_PATH=${PSAP_ODS_SECRET_PATH:-}"
else
    if [[ -z "${PSAP_ODS_SECRET_PATH:-}" ]]; then
        _error "the PSAP_ODS_SECRET_PATH was not provided"
    elif [[ ! -d "$PSAP_ODS_SECRET_PATH" ]]; then
        _error "the PSAP_ODS_SECRET_PATH does not point to a valid directory"
    fi
fi
if [[ "${CONFIG_DEST_DIR:-}" ]]; then
    echo "Using CONFIG_DEST_DIR=$CONFIG_DEST_DIR ..."

elif [[ "${SHARED_DIR:-}" ]]; then
    echo "Using CONFIG_DEST_DIR=\$SHARED_DIR=$SHARED_DIR ..."
    CONFIG_DEST_DIR=$SHARED_DIR
fi

if [[ "${CONFIG_DEST_DIR:-}" ]]; then
    if [[ -e "$CONFIG_DEST_DIR/config.yaml" ]]; then
        cp "$CONFIG_DEST_DIR/config.yaml" "$CI_ARTIFACTS_FROM_CONFIG_FILE" || true
        echo "Configuration file reloaded from '$CONFIG_DEST_DIR/config.yaml'"
    fi
fi

bash "$TESTING_ODS_DIR/configure_overrides.sh"

if [[ "${ARTIFACT_DIR:-}" ]]; then
    cp "$CI_ARTIFACTS_FROM_CONFIG_FILE" "${ARTIFACT_DIR}"
fi
