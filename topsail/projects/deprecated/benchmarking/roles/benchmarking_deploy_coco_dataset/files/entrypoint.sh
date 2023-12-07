#! /bin/bash

set -e
set -u
set -o pipefail
set -x

echo "Installing 'unzip' ..."
dnf install unzip -y --quiet

if [[ -z "${STORAGE_DIR:-}" ]]; then
    STORAGE_DIR=/storage
fi

cat > ${STORAGE_DIR}/checksum.sha256sum <<EOF
113a836d90195ee1f884e704da6304dfaaecff1f023f49b6ca93c4aaae470268  annotations_trainval2017.zip
c7908c3c9f94ba2f3340ebbeec58c25db6be8774f18d68c2f15d0e369d95baba  test2017.zip
69a8bb58ea5f8f99d24875f21416de2e9ded3178e903f1f7603e283b9e06d929  train2017.zip
4f7e2ccb2866ec5041993c9cf2a952bbed69647b115d0f74da7ce8f4bef82f05  val2017.zip
e52f412dd7195ac8f98d782b44c6dd30ea10241e9f42521f67610fbe055a74f8  image_info_test2017.zip
EOF

CRED_FILE=${CRED_FILE:-}
if [[ -n "${CRED_FILE}" ]]; then
    curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
    unzip -q awscliv2.zip
    ./aws/install
    aws configure import --csv file://${CRED_FILE}

    declare -A EXPECTED_NUMBER_OF_FILES=(
        [annotations]=8
        [train2017]=118287
        [val2017]=5000
    )

    for key in "${!EXPECTED_NUMBER_OF_FILES[@]}"; do
        check=$((ls -1q "${STORAGE_DIR}/$key" 2>/dev/null || true) | wc -l)
        if [[ $check != "${EXPECTED_NUMBER_OF_FILES["$key"]}" ]]; then
            rm -rf "${STORAGE_DIR}/$key"
            aws s3 cp "s3://psap-coco-bucket/$key/" "${STORAGE_DIR}/$key" --profile=cocobucket --recursive --quiet
        fi
    done
else
    DOWNLOAD_MAX_TIME_MIN=20
    cd "${STORAGE_DIR}"

    declare -A DIR_PREFIXES=(
        ["test2017.zip"]="zips"
        ["train2017.zip"]="zips"
        ["val2017.zip"]="zips"
        ["annotations_trainval2017.zip"]="annotations"
        ["image_info_test2017.zip"]="annotations"
    )

    DATASET_BASE_URL="http://images.cocodataset.org"
    echo "Using the upstream base URL: $DATASET_BASE_URL"

    for dataset_filename in $(cat checksum.sha256sum | cut -d' ' -f3);
    do
        if [[ -f "$dataset_filename".extracted ]]; then
            echo "$dataset_filename already downloaded and extracted, skipping."
            continue
        fi

        grep "  $dataset_filename" checksum.sha256sum | sed "s/$dataset_filename/-/" > stdin.sha256sum

        if [[ -e "$dataset_filename" ]]; then
            echo "INFO: Found an existing '$dataset_filename'. Checking its sha256sum ..."
            ls -lh "$dataset_filename"
            if ! cat "$dataset_filename" | sha256sum --check "stdin.sha256sum"; then
                echo "INFO: '$dataset_filename' check sum is invalid. Delete it."
                ls -lh "$dataset_filename"
                rm "$dataset_filename"
            else
                echo "INFO: $dataset_filename already available."
                continue
            fi
        fi

        url="$DATASET_BASE_URL"
        url="${url}/${DIR_PREFIXES[$dataset_filename]}"
        cert=""
        url="${url}/$dataset_filename"

        echo "Downloading $url ..."
        touch "${dataset_filename}.url"

        if ! time \
            curl \
            $cert \
            --silent  --fail --show-error \
            --retry 999999 \
            --retry-max-time $(($DOWNLOAD_MAX_TIME_MIN * 60)) \
            --continue-at - \
            "${url}" \
                | tee "$dataset_filename" \
                | sha256sum --check stdin.sha256sum;
        then
            echo "FATAL: failed to download/verify $dataset_filename ..."
            exit 1
        fi
    done

    for dataset_filename in $(cat checksum.sha256sum | cut -d' ' -f3);
    do
        if [[ -f "$dataset_filename".extracted ]]; then
            echo "$dataset_filename already extracted."
            continue
        fi
        echo "Extracting $dataset_filename ..."
        unzip "$dataset_filename" >/dev/null

        touch "${dataset_filename}.extracted"
        echo "Deleting $dataset_filename ..."
        rm -f "$dataset_filename"
    done
fi

echo "All done!"

cd "${STORAGE_DIR}"
ls -lh

exit 0
