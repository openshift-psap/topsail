#!/bin/bash

set -euxo pipefail

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")

# Delete previous resources
"${SCRIPT_DIR}"/delete.sh

# Generate the CA certificate and key
"${SCRIPT_DIR}"/ca/gen_ca.sh

# Generate a client (key and CSR)
"${SCRIPT_DIR}"/client/gen_client.sh

# Change to the client directory because we want the client cert to be placed there
pushd "${SCRIPT_DIR}"/client

    # Sign the client CSR
    "${SCRIPT_DIR}"/ca/sign.sh "${PWD}"/generated_client.csr

    # Delete the client CSR as it is no longer needed
    rm generated_client.csr

    # Concatenate the client key and certificate to one convenient credentials file
    cat generated_client.key generated_client.crt > generated_client_creds.pem 

popd


