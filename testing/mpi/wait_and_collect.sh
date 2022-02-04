#! /bin/bash

set -e
set -u
set -o pipefail
set -x

NAME="hello-world"
NAMESPACE="mpi-benchmark"

mode=$1
destdir="$"

if [ -z "${ARTIFACT_DIR:-}" ]; then
    ARTIFACT_DIR="/tmp/ci-artifacts_$(date +%Y%m%d)"
    mkdir -p "$ARTIFACT_DIR"

    echo "Using '$ARTIFACT_DIR' to store the test artifacts."
else
    echo "Using '$ARTIFACT_DIR' to store the test artifacts."
fi

DEST_DIR="${ARTIFACT_DIR}/$(printf '%03d' $(ls "${ARTIFACT_DIR}/" | grep __ | wc -l))__mpi_$mode"
mkdir -p "$DEST_DIR"

oc delete -f "$mode/mpijob.yaml" -n $NAMESPACE --ignore-not-found
oc create -f "$mode/mpijob.yaml" -n $NAMESPACE

set +e
retries=60 # 10min
while [[ -z "$(oc get mpijob.kubeflow.org/$NAME -ojsonpath={.status.completionTime} -n $NAMESPACE)" ]];
do
    sleep 10
    if oc get pods | grep Failed; then
        echo "One of the Pods failed, bailing out."
        touch "$DEST_DIR/failed"
        break
    fi
    retries=$(($retries - 1))
    if [[ "$retries" == 0 ]]; then
        echo "Job took too long to complete, bailing out."
        touch "$DEST_DIR/failed"
        break
    fi
done

oc get pods \
   -owide \
   -n "$NAMESPACE" \
    | tee "$DEST_DIR/pods.status"

oc logs \
   $(oc get pods \
        -ltraining.kubeflow.org/job-name=$NAME,training.kubeflow.org/job-role=launcher \
        -n "$NAMESPACE" \
        -oname
   ) | tee "$DEST_DIR/launcher.logs"


for worker in $(oc get pods \
                   -ltraining.kubeflow.org/job-name=$NAME,training.kubeflow.org/job-role=worker \
                   -n "$NAMESPACE" \
                   -oname | tr '\n' ' ');
do
    (echo "--- $worker ---" ;  oc logs $worker) \
        | tee -a "$DEST_DIR/$(echo "$worker" | cut -d/ -f2).log"
done

oc get mpijob/$NAME -n "$NAMESPACE" -oyaml > "$DEST_DIR/mpijob.status.yaml"

oc delete mpijob/$NAME -n "$NAMESPACE"

echo "All done, artifacts saved in $DEST_DIR"

[[ -e "$DEST_DIR/failed" ]] && exit 1 || exit 0
