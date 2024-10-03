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
chmod ugo+w "$STORAGE_DIR" || true

echo "---"

df -h "${STORAGE_DIR}"

echo "---"

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

    if ! time git clone "$DOWNLOAD_SOURCE" "$STORAGE_DIR/${SOURCE_NAME}" --depth=1 \
        |& grep -v 'unable to get credential storage lock in 1000 ms: Read-only file system'
    then
        rm -rf "$STORAGE_DIR/${SOURCE_NAME}"
        echo "Clone failed :/"
        exit 1
    fi
    rm -rf "$STORAGE_DIR/${SOURCE_NAME}/.git"

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

    if ! time aws s3 cp "$DOWNLOAD_SOURCE" "${STORAGE_DIR}/${SOURCE_NAME}" --recursive --quiet
    then
        rm -rf "${STORAGE_DIR}/${SOURCE_NAME}"
        echo "Copy failed :/"
        exit 1
    fi
elif [[ "$DOWNLOAD_SOURCE" == "dmf://"* ]];
then
    # CRED_FILE --> github token
    # CRED_FILE_2 --> DMF JSON token

    if [[ -z "${CRED_FILE:-}" ]];
    then
        echo "ERROR: no credentials provided :/"
        exit 1
    fi
    if [[ ! -f "${CRED_FILE}" ]]; then
        echo "ERROR: credentials file does not exist :/"
        exit 1
    fi

    DMF_VERSION=1.7.1
    DMF_WHL_NAME=dmf_lib-${DMF_VERSION}-py3-none-any.whl
    DMF_WHL_FILE="$STORAGE_DIR/../binaries/$DMF_WHL_NAME"
    if [[ ! -f "$DMF_WHL_FILE" ]]; then
        echo "ERROR: DMF wheel file does not exist ($DMF_WHL_FILE) :/"
        exit 1
    fi

    export PATH=$HOME/.local/bin:$PATH
    pip install --quiet "$DMF_WHL_FILE"

    cat > lh-conf.yaml <<EOF
lakehouse:
  environment: PROD
  # please generate your token from https://watsonx-data.cash.sl.cloud9.ibm.com/token
  token: $(cat ${CRED_FILE})
EOF

    namespace=$(echo "$DOWNLOAD_SOURCE" | cut -d/ -f3)
    model_label=$(echo "$DOWNLOAD_SOURCE" | cut -d/ -f4)

    dmf model ls -n "$namespace" "$model_label" -t model_shared

    dmf model pull -n "$namespace" "$model_label" -t model_shared --dir $(realpath "$STORAGE_DIR/${SOURCE_NAME}.tmp")
    # this ^^^ stores the model in $dir/$model_label.$revision ...

    echo "Moving the model to its final storage location ..."
    mv "$STORAGE_DIR/${SOURCE_NAME}.tmp"/* "$STORAGE_DIR/${SOURCE_NAME}/"
    rmdir "$STORAGE_DIR/${SOURCE_NAME}.tmp"

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

find "./${SOURCE_NAME}" ! -path '*/.git/*' -type f -exec sha256sum {} \; | tee -a "${SOURCE_NAME}.sha256sum"

echo "---"

du -sh "./${SOURCE_NAME}"

echo "---"

df -h "${STORAGE_DIR}"

echo "---"

exit 0
