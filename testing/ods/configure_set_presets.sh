#! /bin/bash

set -o errexit
set -o pipefail
set -o nounset
set -o errtrace
set -x

TESTING_ODS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

source "$TESTING_ODS_DIR/../_logging.sh"
source "$TESTING_ODS_DIR/configure.sh"

update_with_presets() {
    local name=$1

    local values
    values=$(get_config "ci_presets.${name}")
    if [[ "$values" == null ]]; then
        _error "Cannot apply ci_presets '$name': key does not exist :/"
    fi
    for key in $(echo "$values" | jq -r '. | keys[]'); do
        local value=$(echo $values | jq -r '.["'$key'"]')

        if [[ "$key" == "extends" ]]; then
            for extend_presets_name in $(echo $value | jq -r '.[]'); do
                update_with_presets "$extend_presets_name"
            done

            continue
        fi

        echo "presets[$name] $key --> $value"
        set_config "$key" "$value"
    done
}

main() {
    # treat 'ci_presets.name'
    local ci_preset_name=$(get_config ci_presets.name)

    if [[ "$ci_preset_name" != null ]]; then
        update_with_presets "$ci_preset_name"
    fi

    # treat 'ci_presets.names'
    local ci_preset_names=$(get_config ci_presets.names)
    if [[ "$ci_preset_names" == null ]]; then
        return 0
    fi

    if [[ "$(jq -c <<< "$ci_preset_names")" == "["* ]]; then
        # it's a list
        while read name; do
            update_with_presets "$name"
        done <<< "$(jq -r .[] <<< "$ci_preset_names")"
    else
        # it's simple entry
        update_with_presets "$ci_preset_names"
    fi
}

main "$@"
