#! /bin/bash

set -Eeuo pipefail

set -x
if [ "$#" -gt 4 ]; then
    echo "Usage: $0 deploy|undeploy <gpu_operator_git_repo> <gpu_operator_git_ref> <gpu_operator_image_tag>"
    exit 1
fi

action="$1"
OPERATOR_GIT_REPO="$2"
OPERATOR_GIT_REF="$3"
OPERATOR_IMAGE_TAG="$4"

OPERATOR_NAME="gpu-operator-from-source"
OPERATOR_NAMESPACE="gpu-operator-ci"
HELM_SOURCE="./deployments/gpu-operator"

# https://stackoverflow.com/a/21189044/341106
function parse_yaml {
   local prefix=$2
   local s='[[:space:]]*' w='[a-zA-Z0-9_]*' fs=$(echo @|tr @ '\034')
   sed -ne "s|^\($s\):|\1|" \
        -e "s|^\($s\)\($w\)$s:$s[\"']\(.*\)[\"']$s\$|\1$fs\2$fs\3|p" \
        -e "s|^\($s\)\($w\)$s:$s\(.*\)$s\$|\1$fs\2$fs\3|p"  $1 |
   awk -F$fs '{
      indent = length($1)/2;
      vname[indent] = $2;
      for (i in vname) {if (i > indent) {delete vname[i]}}
      if (length($3) > 0) {
         vn=""; for (i=0; i<indent; i++) {vn=(vn)(vname[i])("_")}
         printf("%s%s%s=\"%s\"\n", "'$prefix'",vn, $2, $3);
      }
   }'
}

deploy() {
    cd /tmp
    rm -rf gpu-operator
    git clone $OPERATOR_GIT_REPO -b $OPERATOR_GIT_REF --depth 1 gpu-operator

    cd gpu-operator

    set +x
    declare -A HELM_values
    while read line; do
        key=$(echo $line | cut -d= -f1)
        value=$(echo $line | cut -d= -f2 | sed 's/^"//' | sed 's/"$//')
        HELM_values[$key]=$value
    done <<< $(parse_yaml deployments/gpu-operator/values.yaml "")
    set -x

    SKIP_BROKEN_UBI8_DEVICE_PLUGIN=1
    if [ $SKIP_BROKEN_UBI8_DEVICE_PLUGIN == 1 ]; then
        echo "Using default (ubuntu) device plugin image"
        device_plugin_version=${HELM_values[devicePlugin_version]}
    else
        echo "Using ubi8 (maybe broken) device plugin image"
        device_plugin_version=${HELM_values[devicePlugin_version]/-ubuntu*/}-ubi8
    fi

    helm uninstall --namespace $OPERATOR_NAMESPACE $OPERATOR_NAME || true
    #helm template --debug # <-- this is for debugging helm install
    exec helm install \
     $OPERATOR_NAME $HELM_SOURCE \
     --devel \
     \
     --set operator.repository=image-registry.openshift-image-registry.svc:5000/gpu-operator-ci \
     --set operator.image=gpu-operator-ci \
     --set operator.version=${OPERATOR_IMAGE_TAG} \
     \
     --set platform.openshift=true \
     --set operator.defaultRuntime=crio \
     --set nfd.enabled=false \
     \
     --set toolkit.version=${HELM_values[toolkit_version]/-ubuntu*/}-ubi8 \
     --set devicePlugin.version=${device_plugin_version} \
     --set dcgmExporter.version=${HELM_values[dcgmExporter_version]/-ubuntu*/}-ubi8 \
     \
     --namespace $OPERATOR_NAMESPACE \
     --wait
}

undeploy() {
    exec helm uninstall --namespace $OPERATOR_NAMESPACE $OPERATOR_NAME
}

if [ "$action" == deploy ];
then
    deploy
elif [ "$action" == undeploy ];
then
    undeploy
else
    echo "Unknown action command '$action' ..."
    exit 1
fi
