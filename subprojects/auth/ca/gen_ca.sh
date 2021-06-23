#!/bin/bash

set -euxo pipefail

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")

openssl genrsa -out $SCRIPT_DIR/generated_ca.key 4096
openssl req -new -config $SCRIPT_DIR/csr.cnf -x509 -days 365 -key $SCRIPT_DIR/generated_ca.key -out $SCRIPT_DIR/generated_ca.crt
