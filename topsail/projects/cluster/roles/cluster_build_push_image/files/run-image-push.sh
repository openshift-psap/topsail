#! /bin/bash

set -o pipefail
set -o errexit
set -o nounset

LOCAL_AUTH_FILE=/var/run/secrets/openshift.io/push/.dockercfg
REMOTE_AUTH_FILE=/var/run/secrets/quay.io/push/.dockerconfigjson

echo "Local image: '$LOCAL_IMAGE'"
REMOTE_IMAGE=$REMOTE_REPO:$IMAGE_TAG

echo "Destination: $REMOTE_IMAGE"
set -x

(echo "{ \"auths\": "; cat "$LOCAL_AUTH_FILE"; echo "}") > /tmp/.dockercfg_local
podman pull --tls-verify=false --authfile /tmp/.dockercfg_local "$LOCAL_IMAGE"
podman tag "$LOCAL_IMAGE" "$REMOTE_IMAGE"
podman push --tls-verify=false --authfile "$REMOTE_AUTH_FILE" "$REMOTE_IMAGE"
