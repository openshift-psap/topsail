#! /bin/bash

set -o pipefail
set -o errexit
set -o nounset
set -o errtrace
set -x

TOPSAIL_DIR=$(pwd)

GIT_REPO=opendatahub-io/caikit-tgis-serving
GIT_REF=3c69b15146a4627d0031361e20bcc0c8c15e40d4

rm -rf /tmp/caikit-tgis-serving

cd /tmp
git clone --quiet https://github.com/$GIT_REPO

cd caikit-tgis-serving/demo/kserve
git fetch --quiet origin "$GIT_REF"
git checkout FETCH_HEAD

git show --no-patch

POC_DIR=${TOPSAIL_DIR}/projects/kserve/testing/poc/
cp scripts/install/{kserve-install.sh,1-prerequisite-operators.sh,2-required-crs.sh,3-only-kserve-install.sh,check-env-variables.sh} "$POC_DIR"

cp scripts/install/{env.sh,utils.sh} "$POC_DIR"

cp custom-manifests/opendatahub/kserve-dsc.yaml "${POC_DIR}/custom-manifests/opendatahub"
