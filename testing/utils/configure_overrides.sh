#! /bin/bash

set -o errexit
set -o pipefail
set -o nounset
set -o errtrace
set -x

TESTING_UTILS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

source "$TESTING_UTILS_DIR/configure.sh"

do_override() {
    echo "Configuration overrides:"
    while read full_line; do
        line=$(echo "$full_line" | cut -d'#' -f1)
        if [[ -z "$line" ]]; then
            continue
        fi
        key=$(echo "$line" | cut -d: -f1)
        value=$(echo "$line" | cut -d: -f2- | cut -d\' -f2)
        echo "$key --> '$value'"
        set_config "$key" "$value"
    done < $(cat ${ARTIFACT_DIR:-}/variable_overrides.yaml | yq '. | to_entries[] | ""+.key+"="+(.value | tostring)' -r)
    # this ^^^ converts the YAML file to a key=value file, with each value in a single line
}

main() {
    if ! [[ -f "${ARTIFACT_DIR:-}/variable_overrides.yaml" ]]; then
        echo "Nothing to override."
        return 0
    fi

    do_override
    return
}

main "$@"
