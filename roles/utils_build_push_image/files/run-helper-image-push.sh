#! /bin/bash

set -o pipefail
set -o errexit
set -o nounset
set -x

(echo "{ \"auths\": " ; cat /var/run/secrets/openshift.io/push/.dockercfg ; echo "}") > /tmp/.dockercfg_local
podman pull --tls-verify=false --authfile /tmp/.dockercfg_local $LOCAL_IMAGE
podman tag $LOCAL_IMAGE quay.io/$QUAY_REPO:$IMAGE_TAG
podman push --tls-verify=false --authfile /var/run/secrets/quay.io/push/.dockerconfigjson quay.io/$QUAY_REPO:$IMAGE_TAG
