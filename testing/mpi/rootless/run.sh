#! /bin/bash

set -e
set -u
set -o pipefail
set -x

THIS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

cd ${THIS_DIR}/..

../../toolbox/wdm ensure cluster_is_prepared
../../toolbox/wdm ensure has_mpi_osu_image # only needed for rootless

bash ./wait_and_collect.sh rootless rootless/mpijob.yaml

bash ./wait_and_collect.sh rootless rootless/mpijob-osu.yaml
