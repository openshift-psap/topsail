#! /bin/bash

# this file will be sourced by 'prepare_common.sh'
# it should expose two functions:
# - prepare_lab_environment
# - cleanup_lab_environment

# avoid overwritting anything from the sourcing environment
# (use a prefix like 'LAB_PERFLAB__' to prevent collision)

# do *not* execute anything outside of these functions

# use "$(get_config config.key)" if anything must depend on a config key

# mind that the functions will run with bash safety flags:
# set -o errexit # --> exit on error
# set -o pipefail # --> exit on pipe error
# set -o nounset # --> exit on unset variables
# set -o errtrace # --> inherit 'errexit' in subshells
# set -x # --> call tracing (do not pass secrets via the CLI)

# define 'clusters.sutest.lab.name=perflab' to invoke this template
# as part of the CI workflow

LAB_PERFLAB__NAME="perflab"

lab_environment_prepare_sutest() {
    echo "Nothing to do at the moment to prepare the $LAB_PERFLAB__NAME lab environment"

    touch "$ARTIFACT_DIR/${LAB_PERFLAB__NAME}_lab_prepared"
}



lab_environment_cleanup_sutest() {
    echo "Nothing to do at the moment to clean up the $LAB_PERFLAB__NAME lab environment"

    touch "$ARTIFACT_DIR/${LAB_PERFLAB__NAME}_lab_cleanedup"
}
