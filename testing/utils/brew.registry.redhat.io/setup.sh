#! /bin/bash

set -o errexit
set -o pipefail
set -o nounset
set -o errtrace

THIS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

OCP_PULL_SECRET="secret/pull-secret -n openshift-config"
SERVER=brew.registry.redhat.io
IMAGE_CONTENT_SOURCE_POLICY="$THIS_DIR/brew-registry-icsp.yaml"
IMAGE_CONFIG="$THIS_DIR/image-config.yaml"

echo "Checking if the ICSP already exists ..."
if oc get -f ./brew-registry-icsp.yaml 2>/dev/null; then
    echo "Brew ICSP already exists, assuming that Brew is already configured."
    exit 0
fi

TOKEN_FILE=${1:-}
if [[ -z "${TOKEN_FILE}" || ! -e "${TOKEN_FILE}" ]]; then
    echo "ERROR: $0 expects the path to the $SERVER token file "
    echo "INFO:  usual value is \$PSAP_ODS_SECRET_PATH/brew.registry.redhat.io.token"
    exit 1
fi

set +x # disable 'set -x' / 'bash -x' as credentials are handled with bash variables

pull_secrets=$(oc get $OCP_PULL_SECRET -o json | jq -r '.data.".dockerconfigjson"' | base64 -d | jq)
if [[ "$(echo $pull_secrets  | jq -r ".auths | has(\"$SERVER\")")" == true ]]; then
    echo "INFO: OpenShift pull secrets already contain a key for $SERVER ..."
    exit 0
fi

echo "Updating the OpenShift secrets to allow pull images from $SERVER ..."

token=$(cat "$TOKEN_FILE") # /!\ credential read here

updated_pull_secrets=$(echo "$pull_secrets" | jq --arg token "$token" '.auths["'$SERVER'"] = {auth: $token}')

oc set data $OCP_PULL_SECRET --from-file=.dockerconfigjson=<(echo "$updated_pull_secrets")

echo "Applying the $SERVER ImageContentSourcePolicy"

oc apply -f "$IMAGE_CONTENT_SOURCE_POLICY"

# to access ODH nightlies in registry-proxy.engineering.redhat.com
# without hitting certificate errors
oc apply -f "$IMAGE_CONFIG"

echo "Done."
