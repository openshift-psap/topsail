#!/bin/bash
#
#Store the machine set name
json_input=$(cat ${1})
instance_type=${2}
machinesetname=$(echo ${json_input} |jq -c '.metadata.name' |sed -e 's/worker/gpu/' |sed -e 's/^"//' -e 's/"$//' )
selflinkname=$(echo ${json_input} |jq -c '.metadata.selfLink' |sed -e 's/worker/gpu/' |sed -e 's/^"//' -e 's/"$//')

# Change the values for instance type and machine set name
# clean the status key=value
echo ${json_input} |jq --arg instance_type "${instance_type}" '.spec.template.spec.providerSpec.value.instanceType = $instance_type' \
	|jq --arg machinesetname "${machinesetname}" '.metadata.name = $machinesetname' \
	|jq --arg selflinkname "${selflinkname}" '.metadata.selfLink = $selflinkname' \
	|jq --arg machinesetname "${machinesetname}" '.spec.selector.matchLabels."machine.openshift.io/cluster-api-machineset" = $machinesetname' \
	|jq -c --arg machinesetname "${machinesetname}" '.spec.template.metadata.labels."machine.openshift.io/cluster-api-machineset" = $machinesetname' \
	|jq -c '.status = ""' \
	|sed -e 's/,\"status\":\"\"//' \
	|jq .
