#! /bin/bash

if [ -n "$BASH_VERSION" ]; then
    # assume Bash
    TESTING_UTILS_LOCALCI_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
elif [ -n "$ZSH_VERSION" ]; then
    # assume ZSH
    TESTING_UTILS_LOCALCI_DIR=${0:a:h}
elif [[ -z "${TESTING_UTILS_LOCALCI_DIR:-}" ]]; then
     echo "Shell isn't bash nor zsh, please expose the directory of this file with TESTING_UTILS_LOCALCI_DIR."
     exit 1
fi

export TOPSAIL_FROM_COMMAND_ARGS_FILE=${TESTING_UTILS_LOCALCI_DIR}/command_args.yml.j2
export TOPSAIL_FROM_CONFIG_FILE=${TESTING_UTILS_LOCALCI_DIR}/config.yaml
