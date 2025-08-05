#! /bin/bash

# checks the status of the Podman Machine for API Remoting
# return values:
#  0 ==> running with API Remoting support
# 10 ==> running vfkit VM instead of krunkit
# 11 ==> krunkit not running
# 12 ==> krunkit running without API Remoting
# 2x ==> script cannot run correctly

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

if lsof -c vfkit > /dev/null; then
    echo "PodMan Machine running with VFKit (not compatible with the API Remoting support)"
    exit 10
fi

lsof_virgl=$(lsof -c krunkit || true | grep virglrenderer || true)

if [[ -z "$lsof_virgl" ]]; then
    echo "krunkit not running"
    exit 11
fi

# using the version identifier to test the API Remoting support:
#
# if the version identifier is found, then we assume that the right
# krunkit/libkrun/libvirglrenderer are running.

if [[ "$lsof_virgl" != *"$version"* ]]; then
    echo "krunkit running WITHOUT API Remoting support"
    exit 12
fi

echo "krunkit running with API Remoting support"

exit 0
