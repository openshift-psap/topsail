#! /bin/bash

set -e
set -u
set -o pipefail
set -x

BASE_PORT=8440

CERT="$SSHLESS_SECRET_PATH/tls.crt"
KEY="$SSHLESS_SECRET_PATH/tls.key"

echo "> args: $*"
while [[ "$1" == "-o" ]]; do
    shift
    echo "> ignore SSH arg: $1"
    shift
done

dest_hostname="$1"
shift
echo "> hostname: $dest_hostname"
echo "> command: $*"

while ! echo "SYNC" \
        | openssl s_client \
                  -connect $dest_hostname:$BASE_PORT \
                  -cert "$CERT" \
                  -key "$KEY" \
                  -quiet -verify_quiet;
do
    echo "Synchronization with $dest_hostname:$BASE_PORT failed, retrying in 5s ..."
    sleep 5
done

echo "$*" \
    | openssl s_client \
              -connect $dest_hostname:$BASE_PORT \
              -cert "$CERT" \
              -key "$KEY" \
              -quiet -verify_quiet;

RET=$(openssl s_client \
              -connect $dest_hostname:$(($BASE_PORT + 1)) \
              -cert "$CERT" \
              -key "$KEY" \
              -quiet -verify_quiet)

# parse return code and exit accordingly
echo "==> $RET <=="
