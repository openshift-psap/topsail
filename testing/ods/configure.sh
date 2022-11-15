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
    key=${1:-}
    value=${2:-}

    if [[ -z "$key" || -z "$value" ]]; then
        error "set_config key value are both mandatory"
    fi

    yq --yaml-roundtrip --in-place --argjson value "$(echo "$value" | yq)" ".$key = \$value" "$CI_ARTIFACTS_FROM_CONFIG_FILE"

    if [[ "${ARTIFACT_DIR:-}" ]]; then
        cp "$CI_ARTIFACTS_FROM_CONFIG_FILE" "${ARTIFACT_DIR}"
    fi
}

set_config_from_pr_arg() {
    local arg_idx=${1:-}
    local config_key=${2:-}
    local optional=${3:-}

    local warn_missing=1
    if [[ "$optional" == "--optional" ]]; then
        warn_missing=0
    fi

    if [[ -z "$arg_idx" ]]; then
        if [[ "$warn_missing" == 1 ]]; then
            _error "set_config_from_pr_ar '$arg_idx' '$config_key': arg_idx missing"
        fi

        return
    fi

    if [[ -z "$config_key" ]]; then
        _error "set_config_from_pr_ar '$arg_idx' '$config_key': config_key missing"
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


# use this function to get a flat version of the configuration
# the flat key/value pairs can be used to configure the test in the Github PR.
flat_config() {
    local prefix=${1:-}
    if [[ "$prefix" ]]; then
        prefix="$prefix "
    fi
    local yaml_file=$CI_ARTIFACTS_FROM_CONFIG_FILE
    local s='[[:space:]]*' w='[a-zA-Z0-9_]*' fs=$(echo @|tr @ '\034')

    yq -y . "$yaml_file" |\
        sed -ne "s|^\(${s}\):|\1|" \
            -e "s|^\(${s}\)\(${w}\)${s}:${s}[\"']\(.*\)[\"']${s}\$|\1${fs}\2${fs}\3|p" \
            -e "s|^\(${s}\)\(${w}\)${s}:${s}\(.*\)${s}\$|\1${fs}\2${fs}\3|p" | \
        awk -F${fs} '{
      indent = length($1)/2;
      vname[indent] = $2;
      for (i in vname) {if (i > indent) {delete vname[i]}}
      if (length($3) > 0) {
         vn=""; for (i=0; i<indent; i++) {vn=(vn)(vname[i])(".")}
         printf("%s%s%s=%s\n", "'$prefix'",vn, $2, $3);
      }
   }'
}
