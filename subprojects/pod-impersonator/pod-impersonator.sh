#! /bin/bash

set -o errexit
set -o pipefail
set -o nounset
set -o errtrace

trap "exit" INT TERM
trap "kill 0" EXIT

SSH_POD_PORT=2222
SSH_LOCAL_PORT=2222
SSH_SERVER="1000@localhost -p$SSH_LOCAL_PORT"

if [[ -z "${1:-}" ]]; then
    echo "ERROR: A deployment name in the local namespace should be passed passed as argument ..."
    echo "Available deployments:"
    oc get deploy '-ojsonpath={range .items[*]}{"- "}{.metadata.name}{"\n"}{end}'
    exit 1
fi

deployment_name=$1

ssh_public_key=${SSH_PUBLIC_KEY:-}

if [[ -z "$ssh_public_key" ]]; then
  ssh_public_key=$(cat "$HOME/.ssh/id_rsa.pub")
fi

deployment=$(oc get "deploy/$deployment_name" -ojson)
labels=$(echo "$deployment" | jq .spec.template.metadata.labels)
echo "Labels: $labels"
ports=$(echo "$deployment" | jq .spec.template.spec.containers[0].ports)
echo "Ports: $ports"

oc scale --replicas=0 "deploy/$deployment_name"

oc delete --ignore-not-found -f pod-impersonator.yaml
cat pod-impersonator.yaml \
  | yq --arg public_key "$ssh_public_key" '.spec.containers[0].env[0].value = $public_key' \
  | yq --argjson labels "$labels" '.metadata.labels = $labels' \
  | yq --argjson ports "$ports" '.spec.containers[0].ports = $ports' \
  | oc apply -f-

echo "Waiting for the pod to start running ..."
while [[ $(oc get  -f ./pod-impersonator.yaml -ojsonpath={.status.phase}) != "Running" ]]; do
    echo -n .
done
echo "Running."


echo "## Launching the SSH port forwarding ..."

command="oc port-forward pod/pod-impersonator-ssh-server $SSH_POD_PORT:$SSH_LOCAL_PORT"
echo "$command"
$command &
echo

echo "Waiting for the SSH connection to start working ..."
while ! ssh $SSH_SERVER true 2>/dev/null; do
    echo -n .
    sleep 1
done
echo "Connected."

echo "## Launch the application port tunnels ..."

idx=0
for port in $(echo "$ports" | jq -c .[]); do
    name=$(echo "$port" | jq .name)
    containerPort=$(echo "$port" | jq .containerPort)
    local_app_port=$containerPort
    command="ssh -R "$containerPort:localhost:$local_app_port" $SSH_SERVER -N"
    echo "# $name $containerPort (remote) --> $local_app_port (local)"
    echo "$command"
    $command &
    idx=$((idx + 1))
done

wait
