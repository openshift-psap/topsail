#! /bin/bash

set -e
set -u
set -o pipefail
set -x

THIS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd ${THIS_DIR}

SUBJECT="/C=DE/ST=NRW/L=Berlin/O=My Inc/OU=DevOps/CN=www.example.com/emailAddress=dev@www.example.com"
openssl req -nodes -x509 \
        -newkey rsa:2048 \
        -keyout tls.key \
        -out tls.crt \
        -subj "$SUBJECT"

oc delete secret/sshless-secret -n mpi-benchmark --ignore-not-found
oc create secret tls sshless-secret \
   -n mpi-benchmark \
   --key=tls.key \
   --cert=tls.crt

rm tls.key tls.crt

oc delete cm/sshless-scripts -n mpi-benchmark --ignore-not-found
oc create cm sshless-scripts -n mpi-benchmark \
   --from-file=connect.sh=connect.sh \
   --from-file=server.py=server.py

cd ${THIS_DIR}/..

../../toolbox/wdm ensure cluster_is_prepared
../../toolbox/wdm ensure has_mpi_python_base_image

exec bash ./wait_and_collect.sh sshless
