if [ -n "$BASH_VERSION" ]; then
    # assume Bash
    TESTING_LOCAL_CI_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
elif [ -n "$ZSH_VERSION" ]; then
    # assume ZSH
    TESTING_LOCAL_CI_DIR=${0:a:h}
elif [[ -z "${TESTING_LOCAL_CI_DIR:-}" ]]; then
     echo "Shell isn't bash nor zsh, please expose the directory of this file with TESTING_LOCAL_CI_DIR."
     false
fi

export CI_ARTIFACTS_FROM_COMMAND_ARGS_FILE=${TESTING_LOCAL_CI_DIR}/command_args.yaml
export CI_ARTIFACTS_FROM_CONFIG_FILE=${TESTING_LOCAL_CI_DIR}/config.yaml
