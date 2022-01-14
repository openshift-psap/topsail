#! /bin/bash

set -o pipefail
set -o errexit
set -o nounset
set -x

(echo "{ \"auths\": " ; cat /var/run/secrets/openshift.io/push/.dockercfg ; echo "}") > /tmp/.dockercfg_local
podman pull --tls-verify=false --authfile /tmp/.dockercfg_local $LOCAL_IMAGE
podman ps
