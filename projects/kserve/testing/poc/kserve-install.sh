#!/bin/bash

set -o pipefail
set -o errexit
set -o nounset
set -o errtrace
set -x

source "$(dirname "$(realpath "$0")")/env.sh"
source "$(dirname "$(realpath "$0")")/utils.sh"

# Environment variables
# - CHECK_UWM: Set this to "false", if you want to skip the User Workload Configmap check message
# - TARGET_OPERATOR: Set this among odh, rhods or brew, if you want to skip the question in the script.

source check-env-variables.sh

#./1-prerequisite-operators.sh
./2-required-crs.sh
