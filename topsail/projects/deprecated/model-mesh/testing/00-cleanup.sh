#!/bin/bash

THIS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
source "$THIS_DIR/config.sh"

oc delete ns ${MINIO_NS}
for i in $(seq 1 ${NS_COUNT})
    do oc delete ns/${NS_BASENAME}-${i}
done


