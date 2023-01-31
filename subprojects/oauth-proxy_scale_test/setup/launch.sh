#! /bin/bash

set -o errexit
set -o pipefail
set -o nounset
set -o errtrace
set -x

NAMESPACE=oauth-proxy
oc new-project $NAMESPACE --skip-config-write || true
oc apply -f oauth-proxy.yaml -n $NAMESPACE # must be in the oauth-proxy namespace 

DIR=$PWD
cd ../../../
./run_toolbox.py cluster deploy_nginx_server $NAMESPACE "$DIR"
