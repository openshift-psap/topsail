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

OPERATOR_NAME="${OPERATOR_NAME:-gpu-operator-from-source}"
OPERATOR_NAMESPACE="${OPERATOR_NAMESPACE:-gpu-operator-ci}"

NFD_ENABLED="${NFD_ENABLED:-false}"

if [ "${ARTIFACT_DIR:-}" ]; then
    EXTRA_LOGS_DIR="${ARTIFACT_DIR}/$(date +%H%M%S)__helm_deploy_operator"
    mkdir -p "${EXTRA_LOGS_DIR}"
    echo "Using $EXTRA_LOGS_DIR to store helm logs."
    exec > "${EXTRA_LOGS_DIR}/_helm_deploy_operator.log"
    exec 2>&1

else
    EXTRA_LOGS_DIR=""
    echo "ARTIFACT_DIR not set, not storing helm log artifacts."
fi


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

deploy_from_helm() {
    if [ ! "$#" -eq 1 ]; then
        echo "Usage: $script_name deploy_from_helm <version>"
        exit 1
    fi

    HELM_VERSION="${1}"

    HELM_REPO_NAME="nvidia"
    HELM_REPO_ADDR="https://nvidia.github.io/gpu-operator"
    HELM_REPO_PROJ="gpu-operator"

    helm repo add $HELM_REPO_NAME $HELM_REPO_ADDR
    helm repo update

    YAML_VALUES=$(mktemp /tmp/gpu-operator_helm_values.XXXXXX.yaml)
    curl https://raw.githubusercontent.com/NVIDIA/gpu-operator/${HELM_VERSION}/deployments/gpu-operator/values.yaml -s > $YAML_VALUES

    HELM_CUSTOM_OPTIONS="--version ${HELM_VERSION}"

    deploy_operator "${YAML_VALUES}" "${HELM_CUSTOM_OPTIONS}" "${HELM_REPO_NAME}/${HELM_REPO_PROJ}"
}

deploy_from_commit() {
    if [ ! "$#" -eq 3 ]; then
        echo "Usage: $script_name deploy_from_commit <gpu_operator_git_repo> <gpu_operator_git_ref> <gpu_operator_image_tag>"
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

    if [ "${EXTRA_LOGS_DIR}" ]; then
        git show --quiet > "${EXTRA_LOGS_DIR}/gpu_operator.commit"
    fi

    HELM_CUSTOM_OPTIONS="--set operator.repository=image-registry.openshift-image-registry.svc:5000/gpu-operator-ci \
     --set operator.image=gpu-operator-ci \
     --set operator.version=${OPERATOR_IMAGE_TAG}"

    YAML_VALUES="deployments/gpu-operator/values.yaml"
    HELM_SOURCE="./deployments/gpu-operator"

    deploy_operator "${YAML_VALUES}" "${HELM_CUSTOM_OPTIONS}" "${HELM_SOURCE}"
}

deploy_operator() {
    YAML_VALUES="$1"
    HELM_CUSTOM_OPTIONS="$2"
    HELM_SOURCE="$3"

    set +x
    declare -A HELM_values
    while read line; do
        key=$(echo $line | cut -d= -f1)
        value=$(echo $line | cut -d= -f2 | sed 's/^"//' | sed 's/"$//')
        HELM_values[$key]=$value
    done <<< $(parse_yaml ${YAML_VALUES} "")
    set -x

    device_plugin_version=${HELM_values[devicePlugin_version]/%-*}-ubi8
    if [[ "$device_plugin_version" == "v0.7.1-ubi8" ]]; then
        echo "WARNING: cannot use devicePlugin.version=$device_plugin_version"
        device_plugin_version="v0.7.3-ubi8"
        echo "WARNING: using devicePlugin.version=$device_plugin_version instead."
    fi

    helm uninstall --namespace $OPERATOR_NAMESPACE $OPERATOR_NAME 2>/dev/null || true
    oc delete crd/clusterpolicies.nvidia.com --ignore-not-found=true

    helm_args="\
     $OPERATOR_NAME $HELM_SOURCE \
     --devel \
     \
     $HELM_CUSTOM_OPTIONS \
     \
     --set platform.openshift=true \
     --set operator.defaultRuntime=crio \
     --set nfd.enabled=${NFD_ENABLED} \
     \
     --set toolkit.version=${HELM_values[toolkit_version]%-*}-ubi8 \
     --set devicePlugin.version=${device_plugin_version} \
     --set dcgmExporter.version=${HELM_values[dcgmExporter_version]%-*}-ubi8 \
     \
     --namespace $OPERATOR_NAMESPACE \
     --wait"

    if [ "${EXTRA_LOGS_DIR}" ]; then
        helm template --debug $helm_args > "${EXTRA_LOGS_DIR}/helm_deploy.yaml"
    fi

    exec helm install $helm_args
}

undeploy() {
    exec helm uninstall --namespace $OPERATOR_NAMESPACE $OPERATOR_NAME
}

cleanup() {
    echo "Delete possible stalled GPU-operator resources from failed undeployment"
    set -x
    oc delete --ignore-not-found=true ServiceAccount     gpu-operator -n gpu-operator;
    oc delete --ignore-not-found=true ClusterRole        gpu-operator;
    oc delete --ignore-not-found=true ClusterRoleBinding gpu-operator;
    oc delete --ignore-not-found=true Namespace          gpu-operator-resources;
    oc delete --ignore-not-found=true SecurityContextConstraints restricted-readonly;
    if oc get crd/clusterpolicies.nvidia.com 2>/dev/null; then
        # this (below) fails if the type ClusterPolicy doesn't exist
        oc delete --ignore-not-found=true ClusterPolicy      cluster-policy;
    fi
    oc delete --ignore-not-found=true crd clusterpolicies.nvidia.com
}

if [ "$action" == deploy_from_commit ];
then
    deploy_from_commit "$@"
elif [ "$action" == deploy_from_helm ];
then
    deploy_from_helm "$@"
elif [ "$action" == undeploy ];
then
    undeploy
elif [ "$action" == cleanup ];
then
    cleanup
else
    echo "Unknown action command '$action' ..."
    exit 1
fi
