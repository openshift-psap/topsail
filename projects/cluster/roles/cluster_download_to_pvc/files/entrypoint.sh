#! /bin/bash

set -e
set -u
set -o pipefail
set -x


if [[ -z "${STORAGE_DIR:-}" ]]; then
    STORAGE_DIR=/storage
fi

mkdir -p "$STORAGE_DIR"

if [[ "$CLEAN_FIRST" == True ]]; then
    rm "$STORAGE_DIR"/* -rf
fi

if [[ "$DOWNLOAD_SOURCE" == "s3://"* ]];
then
    if [[ -z "${CRED_FILE_DIR:-}" ]];
    then
        echo "ERROR: no creds provided :/"
        exit 1
    fi
    echo "Building AWS cli ..."
    curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
    unzip -q awscliv2.zip
    ./aws/install

    aws configure import --csv file://${CRED_FILE}

    aws s3 cp "$DOWNLOAD_SOURCE" "${STORAGE_DIR}/" --recursive --quiet
else
    DOWNLOAD_MAX_TIME_MIN=20
    cd "${STORAGE_DIR}"

    echo "Downloading $DOWNLOAD_SOURCE ..."

    if ! time curl -O \
         --silent  --fail --show-error \
         --retry 999999 \
         --retry-max-time $(($DOWNLOAD_MAX_TIME_MIN * 60)) \
         --continue-at - \
         "${DOWNLOAD_SOURCE}";
    then
        echo "FATAL: failed to download from ${DOWNLOAD_SOURCE} ..."
        exit 1
    fi
fi

echo "All done!"

cd "${STORAGE_DIR}"
find

exit 0
