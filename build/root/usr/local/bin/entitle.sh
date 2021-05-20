#! /bin/bash -e

set -o pipefail
set -o errexit
set -o nounset
set -x

if ! [ -f toolbox/entitlement/test.sh ]; then
  echo "FATAL: entitlement scripts not found in $PWD/toolbox/entitlement/"
  echo "INFO: $0 is intended only for running in the 'OpenShift PSAP CI artifacts' image. (INSIDE_CI_IMAGE=$INSIDE_CI_IMAGE)"
  exit 1
fi

extract_entitlement_key() {
    resource=$1
    key=$2
    RESOURCE_NAME=50-entitlement-pem
    cat "$resource" \
        | yq . \
        | jq -r -c 'select(.metadata.name=="'${RESOURCE_NAME}'")|.spec.config.storage.files[0].contents.source' \
        | sed 's|data:text/plain;charset=utf-8;base64,||g' \
        | base64 -d \
        > "$key"
}

echo "INFO: Testing if the cluster is already entitled ..."
if toolbox/entitlement/test.sh --no-inspect; then
    echo "INFO: Cluster already entitled, skipping entitlement."
    exit 0
fi

ENTITLEMENT_SECRET_PATH=/var/run/psap-entitlement-secret
ENTITLEMENT_VERSION=${ENTITLEMENT_SECRET_PATH}/version

ENTITLEMENT_PEM=${ENTITLEMENT_PEM:-${ENTITLEMENT_SECRET_PATH}/entitlement.pem}
ENTITLEMENT_RESOURCES=${ENTITLEMENT_RESOURCES:-${ENTITLEMENT_SECRET_PATH}/01-cluster-wide-machineconfigs.yaml}
ENTITLEMENT_REPO_CA=${ENTITLEMENT_REPO_CA:-${ENTITLEMENT_SECRET_PATH}/ops-mirror.pem}

echo "INFO: info about the entitlement secret:"
md5sum ${ENTITLEMENT_SECRET_PATH}/* || true
if [[ -e "$ENTITLEMENT_VERSION" ]]; then
    echo "INFO: Version of the secret vault:"
    cat "$ENTITLEMENT_VERSION"
fi


if [[ -e "$ENTITLEMENT_RESOURCES" && ! -e "$ENTITLEMENT_PEM" ]]; then
    echo "INFO: found entitlement resource file but no entitlement key."

    ENTITLEMENT_PEM=/tmp/key.pem

    echo "INFO: extracting the key from the resource file..."
    echo "INFO: $ENTITLEMENT_RESOURCES --> $ENTITLEMENT_PEM"

    extract_entitlement_key $ENTITLEMENT_RESOURCES $ENTITLEMENT_PEM
fi

if [ ! -e "$ENTITLEMENT_PEM" ]; then
    if [ -z "$ENTITLEMENT_PEM" ]; then
        echo "INFO: no entitlement key provided (ENTITLEMENT_PEM)"
    else
        echo "INFO: entitlement key doesn't exist (ENTITLEMENT_PEM=$ENTITLEMENT_PEM)"
    fi
    echo "FATAL: cluster isn't entitled and not entitlement key was provided."
    exit 1
fi

echo "INFO: Deploying the entitlement with PEM key from ${ENTITLEMENT_PEM}"
toolbox/entitlement/deploy.sh --pem "${ENTITLEMENT_PEM}"

if ! toolbox/entitlement/wait.sh; then
    echo "FATAL: Failed to properly entitle the cluster, cannot continue."
    exit 1
fi
