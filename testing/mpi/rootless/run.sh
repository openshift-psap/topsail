#! /bin/bash

set -e
set -u
set -o pipefail
set -x

THIS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

echo "Nothing to do to prepare rootless."

cd ${THIS_DIR}/..
exec bash ./wait_and_collect.sh rootless
