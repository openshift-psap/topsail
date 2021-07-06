#! /bin/bash

set -e
set -u
set -o pipefail
set -x

cd /storage

DOWNLOAD_MAX_TIME_MIN=20

cat > checksum.md5sum <<EOF
77ad2c53ac5d0aea611d422c0938fb35  test2017.zip
cced6f7f71b7629ddf16f17bbcfab6b2  train2017.zip
442b8da7639aecaf257c1dceb8ba8c80  val2017.zip
f4bbac642086de4f52a3fdda2de5fa2c  annotations_trainval2017.zip
EOF

if [[ -z "${DATASET_BASE_URL:-}" ]]; then
    DATASET_BASE_URL="https://....."
    echo "Using the upstream base URL: $DATASET_BASE_URL"
fi

if [[ ! -e "$CERT_FILE" ]]; then
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

    if ! time \
         curl \
         --silent  --fail --show-error \
         --cert "$CERT_FILE" \
         --retry 999999 \
         --retry-max-time $(($DOWNLOAD_MAX_TIME_MIN * 60)) \
         --continue-at - \
         "$DATASET_BASE_URL/$dataset_filename" \
            | tee "$dataset_filename" | md5sum --check stdin.md5sum;
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
