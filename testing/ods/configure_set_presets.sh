#! /bin/bash

set -o errexit
set -o pipefail
set -o nounset
set -o errtrace
set -x

TESTING_ODS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

source "$TESTING_ODS_DIR/../_logging.sh"
source "$TESTING_ODS_DIR/configure.sh"

main() {
    # treat 'ci_presets.name'
    local ci_preset_name=$(get_config ci_presets.name)

    if [[ "$ci_preset_name" != null ]]; then
        apply_preset "$ci_preset_name"
    fi

    # treat 'ci_presets.names'
    local ci_preset_names=$(get_config ci_presets.names)
    if [[ "$ci_preset_names" == null ]]; then
        return 0
    fi

    if [[ "$(jq -c <<< "$ci_preset_names")" == "["* ]]; then
        # it's a list
        while read name; do
            apply_preset "$name"
        done <<< "$(jq -r .[] <<< "$ci_preset_names")"
    else
        # it's simple entry
        apply_preset "$ci_preset_names"
    fi
}

main "$@"
