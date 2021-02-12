#! /bin/bash

set -Eeuo pipefail

set -x
if [ "$#" -lt 1 -o "$#" -gt 4 ]; then
    echo "Usage:"
    echo "  $0 deploy <gpu_operator_git_repo> <gpu_operator_git_ref> <gpu_operator_image_tag>"
    echo "  $0 undeploy"
    exit 1
fi

script_name="$0"
action="$1"
shift

OPERATOR_NAME="gpu-operator-from-source"
OPERATOR_NAMESPACE="gpu-operator-ci"
HELM_SOURCE="./deployments/gpu-operator"

NFD_ENABLED="${NFD_ENABLED:-false}"

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
    if [ ! "$#" -eq 3 ]; then
        echo "Usage: $script_name deploy <gpu_operator_git_repo> <gpu_operator_git_ref> <gpu_operator_image_tag>"
        exit 1
    fi

    OPERATOR_GIT_REPO="$1"
    OPERATOR_GIT_REF="$2"
    OPERATOR_IMAGE_TAG="$3"

    cd /tmp
    rm -rf gpu-operator
    git clone $OPERATOR_GIT_REPO -b $OPERATOR_GIT_REF --depth 1 gpu-operator

    cd gpu-operator

    git show --quiet
    echo

    set +x
    declare -A HELM_values
    while read line; do
        key=$(echo $line | cut -d= -f1)
        value=$(echo $line | cut -d= -f2 | sed 's/^"//' | sed 's/"$//')
        HELM_values[$key]=$value
    done <<< $(parse_yaml deployments/gpu-operator/values.yaml "")
    set -x

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
     --set nfd.enabled=${NFD_ENABLED} \
     \
     --set toolkit.version=${HELM_values[toolkit_version]/-ubuntu*/}-ubi8 \
     --set devicePlugin.version=${HELM_values[devicePlugin_version]/-ubuntu*/}-ubi8 \
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
    deploy "$@"
elif [ "$action" == undeploy ];
then
    undeploy
else
    echo "Unknown action command '$action' ..."
    exit 1
fi
