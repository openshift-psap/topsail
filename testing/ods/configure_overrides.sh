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

main() {
    if ! [[ -f "${ARTIFACT_DIR:-}/variable_overrides" ]]; then
        echo "Nothing to override."
        return 0
    fi

    do_override
}

main "$@"
