#! /bin/bash

if [ -n "$BASH_VERSION" ]; then
    # assume Bash
    TESTING_ANSIBLE_LLM_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
elif [ -n "$ZSH_VERSION" ]; then
    # assume ZSH
    TESTING_ANSIBLE_LLM_DIR=${0:a:h}
elif [[ -z "${TESTING_ANSIBLE_LLM_DIR:-}" ]]; then
     echo "Shell isn't bash nor zsh, please expose the directory of this file with TESTING_ANSIBLE_LLM_DIR."
     false
fi

TESTING_UTILS_DIR="$TESTING_ANSIBLE_LLM_DIR/../utils"

source "$TESTING_UTILS_DIR/configure.sh"
