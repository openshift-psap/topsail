#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset
set -o errtrace
set -x

THIS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
source "$THIS_DIR/config.sh"


# create namespaces first
for i in $(seq 1 ${NS_COUNT})
do
    NS=${NS_BASENAME}-${i}
    oc create ns ${NS}
    oc apply -f ${THIS_DIR}/minio-secret.yaml -n ${NS}
done
unset NS

# start by creating all model mesh instances by adding the first inference endpoint
# of each namespace
for j in $(seq 1 ${MODEL_COUNT})
do
    for i in $(seq 1 ${NS_COUNT})
    do
        NS=${NS_BASENAME}-${i}
        sed s/example-onnx-mnist/example-onnx-mnist-${j}/g ${THIS_DIR}/triton.yaml | oc apply -n ${NS} -f -
    done
done
unset NS

# check for model mesh instances
for i in $(seq 1 ${NS_COUNT})
do
    NS=${NS_BASENAME}-${i}

    until [[ "$(oc get pods -n ${NS} | grep '4/4' |grep Running |wc -l)" == ${MM_POD_COUNT} ]]
    do
        echo "NS:${NS}: Waiting for the model mesh pods"
        sleep 1
    done

    unset NS
done

# test inference endpoints
for i in $(seq 1 ${NS_COUNT})
do
    if [[ "$API_ENDPOINT_CHECK" -eq 0 ]]
    then
	NS=${NS_BASENAME}-${i}
        route=$(oc -n ${NS} get routes example-onnx-mnist-$i --template={{.spec.host}}{{.spec.path}})
        for i in $(seq 1 ${MODEL_COUNT})
        do
            echo "NS:${NS}: Smoke-testing endpoint example-onnx-mnist-$i"
            until curl $CURL_OPTIONS https://${route}/infer -d @${THIS_DIR}/input-onnx.json | jq '.outputs[] | select(.data != null)' &>/dev/null
            do
                echo "S:${NS}: Waiting for inference endpoint example-onnx-mnist-$i"
                sleep 1
            done
        done

	unset NS
    fi
done
