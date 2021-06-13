#!/bin/bash

set -euxo pipefail

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")

openssl genrsa -out ${SCRIPT_DIR}/generated_client.key 4096
openssl req -new -config ${SCRIPT_DIR}/csr.cnf -key ${SCRIPT_DIR}/generated_client.key -out ${SCRIPT_DIR}/generated_client.csr
