#! /bin/bash

set -o pipefail
set -o errexit
set -o nounset
set -o errtrace

SCRIPT_DIR=$(cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd)

version=$(cat "$SCRIPT_DIR/src_info/version.txt")

if [[ -z "$version" ]]; then
  echo "Couldn't find the API Remoting version identifier :/"
  exit 20
fi

# don't fail on this one ;-)
LSOF_VIRGL=$(lsof -c krunkit || true | grep virglrenderer || true)

if [[ "$LSOF_VIRGL" == *"$version"* ]]; then
  echo "krunkit running with API Remoting support"
  exit 0
elif [[ "$LSOF_VIRGL" == *"krunkit"* ]]; then
  echo "krunkit running WITHOUT API Remoting support"
  exit 11
else
  echo "krunkit not running"
  exit 12
fi
