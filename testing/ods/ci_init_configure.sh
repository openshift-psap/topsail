#! /bin/bash

set -o pipefail
set -o errexit
set -o nounset
set -o errtrace
set -x

TESTING_ODS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

source "$TESTING_ODS_DIR/../_logging.sh"
source "$TESTING_ODS_DIR/configure.sh"

if [[ -z "${PSAP_ODS_SECRET_PATH:-}" ]]; then
    _error "the PSAP_ODS_SECRET_PATH was not provided"
elif [[ ! -d "$PSAP_ODS_SECRET_PATH" ]]; then
    _error "the PSAP_ODS_SECRET_PATH does not point to a valid directory"
fi

if ! get_config rhods.deploy_from_catalog; then
    # deploying from the addon. Get the email address from the secret vault.
    set_config rhods.addon.email "$(cat $PSAP_ODS_SECRET_PATH/addon.email)"
fi

bash "$TESTING_ODS_DIR/configure_overrides.sh"

if [[ "${ARTIFACT_DIR:-}" ]]; then
    cp "$CI_ARTIFACTS_FROM_CONFIG_FILE" "${ARTIFACT_DIR}"
fi
