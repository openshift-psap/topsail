#! /bin/bash

set -e
set -u
set -o pipefail
set -x

THIS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd ${THIS_DIR}

oc delete cm/sshdless-script -n mpi-benchmark --ignore-not-found
oc create cm sshdless-script -n mpi-benchmark \
   --from-file=sshd_server.py=sshd_server.py

cd ${THIS_DIR}/..

../../toolbox/wdm ensure cluster_is_prepared
../../toolbox/wdm ensure has_mpi_python_base_image

exec bash ./wait_and_collect.sh sshdless
