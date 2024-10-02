#! /bin/bash

if [ -n "$BASH_VERSION" ]; then
    # assume Bash
    TESTING_THIS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
elif [ -n "$ZSH_VERSION" ]; then
    # assume ZSH
    TESTING_THIS_DIR=${0:a:h}
elif [[ -z "${TESTING_THIS_DIR:-}" ]]; then
     echo "Shell isn't bash nor zsh, please expose the directory of this file with TESTING_THIS_DIR."
     exit 1
fi

TOPSAIL_DIR="$(cd "$TESTING_THIS_DIR/../../.." >/dev/null 2>&1 && pwd )"
TESTING_UTILS_DIR="$TOPSAIL_DIR/testing/utils"

export TOPSAIL_FROM_COMMAND_ARGS_FILE=${TESTING_THIS_DIR}/command_args.yml.j2

if [[ -z "${TOPSAIL_FROM_CONFIG_FILE:-}" ]]; then
    export TOPSAIL_FROM_CONFIG_FILE=${TESTING_THIS_DIR}/config.yaml
fi
echo "Using '$TOPSAIL_FROM_CONFIG_FILE' as configuration file."

source "$TESTING_UTILS_DIR/configure.sh"
