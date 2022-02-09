#! /bin/bash

set -e
set -u
set -o pipefail
set -x

NAME="hello-world"
NAMESPACE="mpi-benchmark"

mode=$1
mpijob_filename=${2:-$mode/mpijob.yaml}


if [[ -z "${ARTIFACT_DIR:-}" ]]; then
    ARTIFACT_DIR="/tmp/ci-artifacts_$(date +%Y%m%d)"
    mkdir -p "$ARTIFACT_DIR"

    echo "Using '$ARTIFACT_DIR' to store the test artifacts."
else
    echo "Using '$ARTIFACT_DIR' to store the test artifacts."
fi

DEST_DIR="${ARTIFACT_DIR}/$(printf '%03d' $(ls "${ARTIFACT_DIR}/" | grep __ | wc -l))__mpi_$mode"
mkdir -p "$DEST_DIR"

oc delete -f "$mpijob_filename" -n $NAMESPACE --ignore-not-found
mpijob_name=$(oc create -f "$mpijob_filename" -n $NAMESPACE -oname)

# remove the resource type 'mpijob.../'
name=${mpijob_name#*/}

set +e
retries=60 # 10min
while [[ -z "$(oc get "$mpijob_name" -ojsonpath={.status.completionTime} -n $NAMESPACE)" ]];
do
    sleep 10
    if oc get pods | grep Failed; then
        echo "WARNING: One of the Pods failed, bailing out."
        touch "$DEST_DIR/${name}_failed"
        break
    fi
    retries=$(($retries - 1))
    if [[ "$retries" == 0 ]]; then
        echo "WARNING: Job took too long to complete, bailing out."
        touch "$DEST_DIR/${name}_failed"
        break
    fi
done

failed_launcher=$(oc get "$mpijob_name" -ojsonpath={.status.replicaStatuses.Launcher.failed})

if [[ "$failed_launcher" && "$failed_launcher" != 0 ]]; then
    echo "WARNING: The MPI Operator detected a failure of the launcher Pod (failed_launcher=$failed_launcher)."
    touch "$DEST_DIR/${name}_failed"
fi

oc get pods \
   -owide \
   -n "$NAMESPACE" \
    | tee "$DEST_DIR/${name}-pods.status"

oc logs \
   $(oc get pods \
        -ltraining.kubeflow.org/job-name="$name",training.kubeflow.org/job-role=launcher \
        -n "$NAMESPACE" \
        -oname
   ) | tee "$DEST_DIR/${name}-launcher.logs"


for worker in $(oc get pods \
                   -ltraining.kubeflow.org/job-name="$name",training.kubeflow.org/job-role=worker \
                   -n "$NAMESPACE" \
                   -oname | tr '\n' ' ');
do
    (echo "--- $worker ---" ;  oc logs $worker) \
        | tee -a "$DEST_DIR/$(echo "$worker" | cut -d/ -f2).log"
done

oc get $mpijob_name -n "$NAMESPACE" -oyaml > "$DEST_DIR/${name}-mpijob.status.yaml"

oc delete $mpijob_name -n "$NAMESPACE"

echo "All done, artifacts saved in $DEST_DIR"

[[ -e "$DEST_DIR/${name}_failed" ]] && exit 1 || exit 0
