#! /bin/bash -e

set -o pipefail
set -o errexit
set -o nounset
set -x

if ! [ -f ./toolbox/entitlement.py ]; then
  echo "FATAL: entitlement script not found in $PWD/toolbox/"
  echo "INFO: $0 is intended only for running in the 'OpenShift PSAP CI artifacts' image. (INSIDE_CI_IMAGE=$INSIDE_CI_IMAGE)"
  exit 1
fi

_expected_fail() {
    # mark the last toolbox step as an expected fail (for clearer
    # parsing/display in ci-dashboard)
    # eg: if cluster doesn't have NFD labels (expected fail), deploy NFD
    # eg: if cluster doesn't have GPU nodes (expected fail), scale up with GPU nodes

    last_toolbox_dir=$(ls ${ARTIFACT_DIR}/*__* -d | tail -1)
    echo "$1" > ${last_toolbox_dir}/EXPECTED_FAIL
}

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
if ./run_toolbox.py entitlement test_cluster --no_inspect; then
    echo "INFO: Cluster already entitled, skipping entitlement."
    exit 0
fi

# mark the failure of "entitlement test_cluster" ^^^ as expected
_expected_fail "Checking if the cluster was entitled"

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
./run_toolbox.py entitlement deploy "${ENTITLEMENT_PEM}"

if ! ./run_toolbox.py entitlement wait; then
    echo "FATAL: Failed to properly entitle the cluster, cannot continue."
    exit 1
fi
