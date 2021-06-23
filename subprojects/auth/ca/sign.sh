#!/bin/bash

set -euxo pipefail

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")

usage() {
    echo "Usage: $0 <CSR file>"
}

if [ "$#" != 1 ]; then
    usage
    exit 1
fi

CSR_FILE=$1

openssl x509 -req -days 3650 -in ${CSR_FILE} -CA ${SCRIPT_DIR}/generated_ca.crt -CAkey ${SCRIPT_DIR}/generated_ca.key -set_serial 01 -out generated_client.crt

echo Saved signed client certificate to ${PWD}/generated_client.crt
