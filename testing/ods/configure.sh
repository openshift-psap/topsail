if [ -n "$BASH_VERSION" ]; then
    # assume Bash
    TESTING_ODS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
elif [ -n "$ZSH_VERSION" ]; then
    # assume ZSH
    TESTING_ODS_DIR=${0:a:h}
elif [[ -z "${TESTING_ODS_DIR:-}" ]]; then
     echo "Shell isn't bash nor zsh, please expose the directory of this file with TESTING_ODS_DIR."
     false
fi

export CI_ARTIFACTS_FROM_COMMAND_ARGS_FILE=${TESTING_ODS_DIR}/command_args.yaml
export CI_ARTIFACTS_FROM_CONFIG_FILE=${TESTING_ODS_DIR}/config.yaml

test_config() {
    key=$1

    test "$(get_config "$key == true")" == "true"
}

get_config() {
    key=$1

    yq -M -r ".$key" "$CI_ARTIFACTS_FROM_CONFIG_FILE"
}

set_config() {
    key=$1
    value=$2

    yq --yaml-roundtrip --in-place --arg value "$value" ".$key = \$value" "$CI_ARTIFACTS_FROM_CONFIG_FILE"

    if [[ "${ARTIFACT_DIR:-}" ]]; then
        cp "$CI_ARTIFACTS_FROM_CONFIG_FILE" "${ARTIFACT_DIR}"
    fi
}

set_config_from_pr_arg() {
    optional=${1:-}
    warn_missing=1
    if [[ "$optional" == "--optional" ]]; then
        warn_missing=0
        shift
    fi

    local arg_idx=${1:-}
    local config_key=${2:-}

    if [[ -z "$arg_idx" ]]; then
        if [[ "$warn_missing" == 1 ]]; then
            _warning "set_config_from_pr_ar '$arg_idx' '$config_key': arg_idx missing"
        fi

        return
    fi

    if [[ -z "$config_key" ]]; then
        _warning "set_config_from_pr_ar '$arg_idx' '$config_key': config_key missing"
        return
    fi

    value=$(get_config "PR_POSITIONAL_ARG_${arg_idx}")
    [[ "$value" == null ]] && return

    set_config "$config_key" "$value"
}


get_command_arg() {
    key=$1
    shift
    ./run_toolbox.py from_config "$@" --show_args "$key"
}
