#!/bin/bash

set -euxo pipefail

cd $SYNC_DESTINATION

# Coco
mkdir -p coco
pushd coco
echo "Downloading COCO to ${PWD}"

CURL_FLAGS=("--fail-early" "--fail")

ANNOTATIONS="http://images.cocodataset.org/annotations"
DATASETS="http://images.cocodataset.org/zips"

for url in $ANNOTATIONS $DATASETS; do
    if [[ $url == $ANNOTATIONS ]]; then
        files=(  annotations_trainval2017.zip )
    elif [[ $url == $DATASETS ]]; then
        files=(train2017.zip val2017.zip test2017.zip)
    fi

    echo "Downloading ${files} from ${url}"
    for fname in ${files[@]}; do
        if [[ ! -f ${fname} ]]; then
            curl ${CURL_FLAGS[@]} ${url}/${fname} -O
        fi
    done
done
popd

touch healthy

