#! /bin/bash

if [[ -z "${CI_ARTIFACTS_FROM_CONFIG_FILE:-}" ]]; then
    echo "ERROR: CI_ARTIFACTS_FROM_CONFIG_FILE not set, cannot proceed."
    exit 1
fi

test_config() {
    key=$1

    test "$(get_config "$key == true")" == "true"
}

get_config() {
    key=$1

    yq -M -r ".$key" "$CI_ARTIFACTS_FROM_CONFIG_FILE"
}

set_config() {
    if ! [[ -v 1 && -v 2 ]]; then
        _error "set_config 'key' 'value' parameters are both mandatory"
    fi

    key=${1}
    value=${2}

    if [[ -z "$value" ]]; then
        # without this, the ARG of '--argjson value ARG' below is empty, and yq/jq aren't happy (not a json value)
        value="''"
    fi

    yq --yaml-roundtrip --in-place --argjson value "$(echo "$value" | yq)" ".$key = \$value" "$CI_ARTIFACTS_FROM_CONFIG_FILE"

    if [[ "${ARTIFACT_DIR:-}" ]]; then
        cp "$CI_ARTIFACTS_FROM_CONFIG_FILE" "${ARTIFACT_DIR}" || true
    fi
}

apply_preset() {
    local name=$1

    local values
    values=$(get_config "ci_presets.${name}")
    if [[ "$values" == null ]]; then
        _error "Cannot apply ci_presets '$name': key does not exist :/"
    fi
    for key in $(echo "$values" | jq -r 'keys_unsorted | .[]'); do
        local value=$(echo $values | jq -r '.['$(echo "$key" | yq)']')

        if [[ "$key" == "extends" ]]; then
            for extend_presets_name in $(echo $value | jq -r '.[]'); do
                apply_preset "$extend_presets_name"
            done

            continue
        fi

        echo "presets[$name] $key --> $value"
        echo "presets[$name] $key --> $value" >> "$ARTIFACT_DIR/presets_applied"
        set_config "$key" "$value"
    done

    preset_names=$(get_config ci_presets.names | jq '. += ["'$name'"] | unique')
    set_config ci_presets.names "$preset_names"
}

set_presets_from_pr_args() {
    local pr_args=$(flat_config | grep PR_POSITIONAL_ARG_ | grep -v PR_POSITIONAL_ARG_0 | cut -d= -f2 | tr ' ' '\n')
    if [[ -z "$pr_args" ]]; then
        echo "No PR positional args."
        return 0
    fi

    while read pr_arg; do
        echo "Apply '$pr_arg' preset from the PR positional args."
        apply_preset "$pr_arg"
    done <<< $pr_args
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
