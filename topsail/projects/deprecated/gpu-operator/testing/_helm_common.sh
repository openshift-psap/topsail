THIS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

HELM_DEPLOY_OPERATOR=$THIS_DIR/_helm_deploy_operator.sh

if [ ! -f "${HELM_DEPLOY_OPERATOR}" ]; then
    echo "WARNING: cannot find the helm deploy script"
    echo "Double check ${ROLE_CUSTOM_COMMIT_RESOURCES_FILE}::${ROLE_CUSTOM_COMMIT_RESOURCES_KEY} and ${HELM_DEPLOY_OPERATOR}"
fi

export OPERATOR_NAME="${OPERATOR_NAME:-gpu-operator}"
export OPERATOR_NAMESPACE="${OPERATOR_NAMESPACE:-gpu-operator}"

echo "Using OPERATOR_NAME=${OPERATOR_NAME} and OPERATOR_NAMESPACE=${OPERATOR_NAMESPACE}"
