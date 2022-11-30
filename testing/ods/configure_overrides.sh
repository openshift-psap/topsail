#! /bin/bash

set -o errexit
set -o pipefail
set -o nounset
set -x

TESTING_ODS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

source "$TESTING_ODS_DIR/configure.sh"

do_override() {
    echo "Configuration overrides:"
    while read line; do
        key=$(echo "$line" | cut -d= -f1)
        value=$(echo "$line" | cut -d= -f2- | cut -d\' -f2)
        echo "$key --> '$value'"
        set_config "$key" "$value"
    done < "${ARTIFACT_DIR:-}/variable_overrides"
}

update_with_presets() {
    local name=$1

    local values=$(get_config "ci_presets.${name}")
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
    if ! [[ -f "${ARTIFACT_DIR:-}/variable_overrides" ]]; then
        echo "Nothing to override."
        exit 0
    fi

    do_override

    local ci_preset_name=$(get_config ci_presets.name)
    if [[ "$ci_preset_name" == null ]]; then
        exit 0
    fi

    update_with_presets "$ci_preset_name"

    # re-do the override, so that preset values can be overriden
    do_override
}

main "$@"
