#! /bin/bash

if [ -n "$BASH_VERSION" ]; then
    # assume Bash
    TESTING_PIPELINES_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
elif [ -n "$ZSH_VERSION" ]; then
    # assume ZSH
    TESTING_PIPELINES_DIR=${0:a:h}
elif [[ -z "${TESTING_PIPELINES_DIR:-}" ]]; then
     echo "Shell isn't bash nor zsh, please expose the directory of this file with TESTING_PIPELINES_DIR."
     false
fi

TESTING_UTILS_DIR="$TESTING_PIPELINES_DIR/../utils"

export CI_ARTIFACTS_FROM_COMMAND_ARGS_FILE=${TESTING_PIPELINES_DIR}/command_args.yml.j2

if [[ -z "${CI_ARTIFACTS_FROM_CONFIG_FILE:-}" ]]; then
    export CI_ARTIFACTS_FROM_CONFIG_FILE=${TESTING_PIPELINES_DIR}/config.yaml
fi
echo "Using '$CI_ARTIFACTS_FROM_CONFIG_FILE' as configuration file."

source "$TESTING_UTILS_DIR/configure.sh"
