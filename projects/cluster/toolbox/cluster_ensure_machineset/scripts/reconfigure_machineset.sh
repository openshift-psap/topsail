#!/bin/bash

json_input=$(cat ${1})
instance_type=${2}
machinesetname=${3}
taint=${4}
instance_type_field=${5}

set -x

if [[ -z "$machinesetname" ]]; then
    # Compute the machine set name
    machinesetname="$(echo ${json_input} | jq -r '.metadata.name')--$(echo ${instance_type} | tr . -)"
fi

jq_taint_node_label=""
jq_taint_machine_label=""
jq_taint=""
if [[ "$taint" ]]; then
    #tain=key=value:effect
    key=$(echo "$taint" | cut -d= -f1)
    value=$(echo "$taint" | cut -d= -f2- | cut -d: -f1)
    effect=$(echo "$taint" | cut -d: -f2)
    jq_taint='.spec.template.spec.taints = [{"effect": "'$effect'", "key": "'$key'", "value": "'$value'"}]'
    jq_taint_machine_label='.spec.template.metadata.labels += {"'$key'": "'$value'"}'
    jq_taint_node_label='.spec.template.spec.metadata.labels += {"'$key'": "'$value'"}'
fi

# Change the values for instance type and machine set name
# Clean the status key=value
echo ${json_input} \
    | jq --arg instance_type "${instance_type}" '.spec.template.spec.providerSpec.value.'$instance_type_field' = $instance_type' \
    | jq --arg machinesetname "${machinesetname}" '.metadata.name = $machinesetname' \
    | jq --arg machinesetname "${machinesetname}" '.spec.selector.matchLabels."machine.openshift.io/cluster-api-machineset" = $machinesetname' \
    | jq -c --arg machinesetname "${machinesetname}" '.spec.template.metadata.labels."machine.openshift.io/cluster-api-machineset" = $machinesetname' \
    | jq -c 'del(.status)|del(.metadata.selfLink)|del(.metadata.uid)' \
    | jq '.spec.replicas = 0' \
    | jq "$jq_taint" \
    | jq "$jq_taint_machine_label" \
    | jq "$jq_taint_node_label"
