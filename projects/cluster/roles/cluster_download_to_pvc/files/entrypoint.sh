#! /bin/bash

set -e
set -u
set -o pipefail
set -x


if [[ -z "${STORAGE_DIR:-}" ]]; then
    STORAGE_DIR=/storage
fi

if [[ "$CLEAN_FIRST" == True ]]; then
    rm "$STORAGE_DIR" -rf
fi

mkdir -p "$STORAGE_DIR"
chmod ugo+w "$STORAGE_DIR"

if [[ "$DOWNLOAD_SOURCE" == "https://huggingface.co/"* ]];
then
    dnf install --quiet -y git-lfs

    if [[ "${CRED_FILE:-}" ]];
    then
        echo "Enabling git 'store' credential helper ..."
        sha256sum "${CRED_FILE}"

        git config --global credential.helper "store --file=$CRED_FILE"
    else
        echo "No credential file passed."
    fi

    git clone "$DOWNLOAD_SOURCE" "$STORAGE_DIR/${SOURCE_NAME}" --depth=1

elif [[ "$DOWNLOAD_SOURCE" == "s3://"* ]];
then
    if [[ -z "${CRED_FILE:-}" ]];
    then
        echo "ERROR: no credentials provided :/"
        exit 1
    fi
    if [[ ! -f "${CRED_FILE}" ]]; then
        echo "ERROR: credentials file does not exist :/"
        exit 1
    fi

    dnf install --quiet -y unzip

    echo "Building AWS cli ..."
    curl -Ssf "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
    unzip -q awscliv2.zip
    ./aws/install

    export AWS_SHARED_CREDENTIALS_FILE=$CRED_FILE

    aws s3 cp "$DOWNLOAD_SOURCE" "${STORAGE_DIR}/${SOURCE_NAME}" --recursive --quiet
else
    cd "${STORAGE_DIR}"

    echo "Downloading $DOWNLOAD_SOURCE ..."

    if ! time curl -O \
         --silent  --fail --show-error \
         "${DOWNLOAD_SOURCE}";
    then
        echo "FATAL: failed to download from ${DOWNLOAD_SOURCE} ..."
        exit 1
    fi
fi

echo "All done!"

cd "${STORAGE_DIR}"

find "./${SOURCE_NAME}" ! -path '*/.git/*' -type f -exec sha256sum {} \;

exit 0
