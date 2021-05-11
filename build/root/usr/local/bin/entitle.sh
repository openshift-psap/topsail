#! /bin/bash -e

set -o pipefail
set -o errexit
set -o nounset

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

echo "Testing if the cluster is already entitled ..."
if toolbox/entitlement/test.sh --no-inspect; then
    echo "Cluster already entitled, skipping entitlement."
    exit 0
fi

ENTITLEMENT_SECRET_PATH=/var/run/psap-entitlement-secret
ENTITLEMENT_PEM=${ENTITLEMENT_PEM:-${ENTITLEMENT_SECRET_PATH}/entitlement.pem}
ENTITLEMENT_RESOURCES=${ENTITLEMENT_RESOURCES:-${ENTITLEMENT_SECRET_PATH}/01-cluster-wide-machineconfigs.yaml}
ENTITLEMENT_REPO_CA=${ENTITLEMENT_REPO_CA:-${ENTITLEMENT_SECRET_PATH}/ops-mirror.pem}

if [[ -e "$ENTITLEMENT_RESOURCES" && ! -e "$ENTITLEMENT_PEM" ]]; then
    echo "INFO: found entitlement resource file but no entitlement key."

    ENTITLEMENT_PEM=/tmp/key.pem

    echo "INFO: extracting the key from the resource file..."
    echo "INFO: $ENTITLEMENT_RESOURCES --> $ENTITLEMENT_PEM"

    extract_entitlement_key $ENTITLEMENT_RESOURCES $ENTITLEMENT_PEM
fi

REPO_CA_FLAG=""
if oc version | grep -q "Server Version: 4.8"; then
    if [ ! -e "$ENTITLEMENT_REPO_CA" ]; then
        echo "WARNING: Running with OCP 4.8 and RHEL-beta repo CA missing..."
    else
        echo "INFO: Using $ENTITLEMENT_REPO_CA as RHEL-beta repo CA"
        REPO_CA_FLAG="--ca $ENTITLEMENT_REPO_CA"
    fi
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

echo "Deploying the entitlement with PEM key from ${ENTITLEMENT_PEM}"
toolbox/entitlement/deploy.sh --pem "${ENTITLEMENT_PEM}" ${REPO_CA_FLAG}

if ! toolbox/entitlement/wait.sh; then
    echo "FATAL: Failed to properly entitle the cluster, cannot continue."
    exit 1
fi
