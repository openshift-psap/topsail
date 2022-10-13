#! /usr/bin/env bash

set -o pipefail
set -o errexit
set -o nounset

# This script is executed from `ci-artifacts` PR, when requesting
# `\test test-pr`.
#
# It looks at the message of the the PR and scans it for a test-path
# directive: > test-path: ... [flags] and executes the test command.
#
# Calling this script on a PR without a `test-path` fails the test
# (exit 1).


THIS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
BASE_DIR="${THIS_DIR}/../"
cd "$BASE_DIR"

if [[ "${ARTIFACT_DIR:-}" ]] && [[ -f "${ARTIFACT_DIR}/variable_overrides" ]]; then
    source "${ARTIFACT_DIR}/variable_overrides"
fi

if [[ -z "${PR_POSITIONAL_ARGS:-}" ]]; then
    echo "ERROR: PR_POSITIONAL_ARGS must be set ..."
    exit 1
fi

testpath=$PR_POSITIONAL_ARGS

if [[ -z "$testpath" ]]; then
    echo "Nothing to test ..."
    exit 1
fi

if [[ -z "${ARTIFACT_DIR:-}" ]]; then
    ARTIFACT_DIR=/tmp
fi

BASE_ARTIFACT_DIR=${ARTIFACT_DIR}

while read cmd;
do
    basename=$(basename "$cmd" | sed 's/ /_/g')
    export ARTIFACT_DIR="${BASE_ARTIFACT_DIR}/${basename}"
    mkdir -p "${ARTIFACT_DIR}"
    cat <<EOF
###
# Running test-path: $cmd
##

Using ARTIFACT_DIR=${ARTIFACT_DIR}

EOF

    bash "${THIS_DIR}/run" $(echo "$cmd")  |& tee "${ARTIFACT_DIR}/test-log.txt"
    echo "---"

done <<< "$testpath"

echo "All done."
