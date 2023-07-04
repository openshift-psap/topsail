#! /bin/bash -e

if [[ "${1:-}" == "" || "${1}" == "-h" || "${1}" == "--help" ]]; then
    cat <<EOF
Fetch metrics from a Pod

Usage: $0 <POD_PORT> <LABEL_SELECTOR> <NAMESPACE> <PROM_GREP_KEY>
Example:
  $0 9400 app=nvidia-dcgm-exporter $GPU_OPERATOR_NAMESPACE '#HELP'
EOF
    exit 0
fi

POD_PORT="$1"
shift
LABEL_SELECTOR="$1"
shift
NAMESPACE="$1"
shift
PROM_GREP_KEY="$1"


METRICS_ENDPOINT="metrics"

LOCAL_PORT=9401

pod_name=$(oc get pods -oname -l$LABEL_SELECTOR -n$NAMESPACE | head -1);
if [ -z "$pod_name" ]; then
    echo "Failed to find a pod for $LABEL_SELECTOR in namespace $NAMESPACE";
    exit 10;
fi;

tries_left=5
oc port-forward ${pod_name} ${LOCAL_PORT}:${POD_PORT} -n $NAMESPACE &
OC_PORT_FWD_PID=$!
trap "kill -9 $OC_PORT_FWD_PID 2>/dev/null" EXIT

pod_output=""
while [ "$pod_output" == "" ]; do
    sleep 1
    pod_output=$(curl localhost:${LOCAL_PORT}/${METRICS_ENDPOINT} 2>/dev/null)
    tries_left=$(($tries_left - 1))
    if [[ $tries_left == 0 ]]; then
        echo "Failed to get any output from ${pod_name}/${METRICS_ENDPOINT} ..."
        exit 11
    fi
done

grep "$PROM_GREP_KEY" <<< ${pod_output}
