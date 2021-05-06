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

entitlement_deployed=0

ENTITLEMENT_PEM=${ENTITLEMENT_PEM:-/var/run/psap-entitlement-secret/entitlement.pem}
if [ -z "$ENTITLEMENT_PEM" ]; then
    echo "INFO: no entitlement key provided (ENTITLEMENT_PEM)"
elif [ ! -e "$ENTITLEMENT_PEM" ]; then
    echo "INFO: entitlement key doesn't exist (ENTITLEMENT_PEM=$ENTITLEMENT_PEM)"
else
    echo "Deploying the entitlement with PEM key from ${ENTITLEMENT_PEM}"
    toolbox/entitlement/deploy.sh --pem ${ENTITLEMENT_PEM}
    entitlement_deployed=1
fi

ENTITLEMENT_RESOURCES=${ENTITLEMENT_RESOURCES:-/var/run/psap-entitlement-secret/01-cluster-wide-machineconfigs.yaml}
if [ "$entitlement_deployed" == 1 ]; then
    # entitlement already deployed
    true
elif [ -z "$ENTITLEMENT_RESOURCES" ]; then
    echo "INFO: no entitlement resource provided (ENTITLEMENT_RESOURCES)"
elif [ ! -e "$ENTITLEMENT_RESOURCES" ]; then
    echo "INFO: entitlement resource file doesn't exist (ENTITLEMENT_RESOURCES=$ENTITLEMENT_RESOURCES)"
else
    ENTITLEMENT_KEY=/tmp/key.pem
    extract_entitlement_key $ENTITLEMENT_RESOURCES $ENTITLEMENT_KEY

    toolbox/entitlement/deploy.sh --pem "${ENTITLEMENT_KEY}"
    entitlement_deployed=1
fi

if [ "$entitlement_deployed" == 0 ]; then
    echo "FATAL: cluster isn't entitled and not entitlement provided (ENTITLEMENT_PEM)"
    exit 1
fi

if ! toolbox/entitlement/wait.sh; then
    echo "FATAL: Failed to properly entitle the cluster, cannot continue."
    exit 1
fi