#! /bin/bash

set -e
set -u
set -o pipefail
set -x

cd /storage

DOWNLOAD_MAX_TIME_MIN=20
CERT_FILE=${CERT_FILE:-}

cat > checksum.md5sum <<EOF
77ad2c53ac5d0aea611d422c0938fb35  test2017.zip
cced6f7f71b7629ddf16f17bbcfab6b2  train2017.zip
442b8da7639aecaf257c1dceb8ba8c80  val2017.zip
f4bbac642086de4f52a3fdda2de5fa2c  annotations_trainval2017.zip
EOF

declare -A DIR_PREFIXES=(
    ["test2017.zip"]="zips"
    ["train2017.zip"]="zips"
    ["val2017.zip"]="zips"
    ["annotations_trainval2017.zip"]="annotations"
)

if [[ -z "$CERT_FILE" ]]; then
    echo "INFO: no cert file provided, downloading from upstream."

    DATASET_BASE_URL="http://images.cocodataset.org"
    echo "Using the upstream base URL: $DATASET_BASE_URL"

elif [[ ! -e "$CERT_FILE" ]]; then
    echo "FATAL: cert file not found ($CERT_FILE)"
    exit 1
fi

echo "Installing 'unzip' ..."
dnf install unzip -y --quiet

for dataset_filename in $(cat checksum.md5sum | cut -d' ' -f3);
do
    if [[ -f "$dataset_filename".extracted ]]; then
        echo "$dataset_filename already downloaded and extracted, skipping."
        continue
    fi

    grep "  $dataset_filename" checksum.md5sum | sed "s/$dataset_filename/-/" > stdin.md5sum

    if [[ -e "$dataset_filename" ]]; then
        echo "INFO: Found an existing '$dataset_filename'. Checking its md5sum ..."
        ls -lh "$dataset_filename"
        if ! cat "$dataset_filename" | md5sum --check "stdin.md5sum"; then
            echo "INFO: '$dataset_filename' check sum is invalid. Delete it."
            ls -lh "$dataset_filename"
            rm "$dataset_filename"
        else
            echo "INFO: $dataset_filename already available."
            continue
        fi
    fi

    url="$DATASET_BASE_URL"
    if [[ -z "$CERT_FILE" ]]; then
        url="${url}/${DIR_PREFIXES[$dataset_filename]}"
        cert=""
    else
        cert="--cert $CERT_FILE"
    fi
    url="${url}/$dataset_filename"

    echo "Downloading $url ..."


    if ! time \
         curl \
         $cert \
         --silent  --fail --show-error \
         --retry 999999 \
         --retry-max-time $(($DOWNLOAD_MAX_TIME_MIN * 60)) \
         --continue-at - \
         "${url}" \
            | tee "$dataset_filename" \
            | md5sum --check stdin.md5sum;
    then
        echo "FATAL: failed to download/verify $dataset_filename ..."
        exit 1
    fi
done

for dataset_filename in $(cat checksum.md5sum | cut -d' ' -f3);
do
    if [[ -f "$dataset_filename".extracted ]]; then
        echo "$dataset_filename already extracted."
        continue
    fi
    echo "Extracting $dataset_filename ..."
    unzip "$dataset_filename" >/dev/null

    touch "$dataset_filename".extracted
    echo "Deleting $dataset_filename ..."
    rm -f "$dataset_filename"
done

echo "All done!"

ls -lh

exit 0
