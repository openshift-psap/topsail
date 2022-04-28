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

ANCHOR="test-path: "

if [[ -z "${PULL_NUMBER:-}" ]]; then
   echo "ERROR: no PULL_NUMBER defined ..."
   exit 1
fi

body="$(curl -sSf "https://api.github.com/repos/openshift-psap/ci-artifacts/pulls/$PULL_NUMBER" | jq -r .body)"

if [[ -z "${body:-}" ]]; then
   echo "ERROR: pull request 'body' is empty ..."
   exit 1
fi

testpaths=$(echo "$body" | { grep "$ANCHOR" || true;} | cut -b$(echo "$ANCHOR" | wc -c)-)

if [[ -z "$testpaths" ]]; then
    echo "Nothing to test in PR $PULL_NUMBER."
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

    bash ${THIS_DIR}/run $(echo "$cmd")  |& tee "${ARTIFACT_DIR}/test-log.txt"
    echo "---"

done <<< "$testpaths"

echo "All done."
