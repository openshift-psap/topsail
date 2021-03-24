ROLE_CUSTOM_COMMIT_RESOURCES_FILE="roles/gpu_operator_deploy_custom_commit/vars/main/resources.yml"
ROLE_CUSTOM_COMMIT_RESOURCES_KEY="gpu_operator_helm_install"
HELM_DEPLOY_OPERATOR=$(cat "${ROLE_CUSTOM_COMMIT_RESOURCES_FILE}" | grep "${ROLE_CUSTOM_COMMIT_RESOURCES_KEY}" | cut -d: -f2 | xargs)

if [ ! -f "${HELM_DEPLOY_OPERATOR}" ]; then
    echo "WARNING: cannot find the helm deploy script"
    echo "Double check ${ROLE_CUSTOM_COMMIT_RESOURCES_FILE}::${ROLE_CUSTOM_COMMIT_RESOURCES_KEY} and ${HELM_DEPLOY_OPERATOR}"
fi

export OPERATOR_NAME="${OPERATOR_NAME:-gpu-operator}"
export OPERATOR_NAMESPACE="${OPERATOR_NAMESPACE:-gpu-operator}"

echo "Using OPERATOR_NAME=${OPERATOR_NAME} and OPERATOR_NAMESPACE=${OPERATOR_NAMESPACE}"
