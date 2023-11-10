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


cp scripts/install/{kserve-install.sh,1-prerequisite-operators.sh,2-required-crs.sh,3-only-kserve-install.sh,check-env-variables.sh} ${TOPSAIL_DIR}/testing/watsonx-serving/poc/

cp scripts/install/{env.sh,utils.sh} ${TOPSAIL_DIR}/testing/watsonx-serving/poc/

cp custom-manifests/opendatahub/kserve-dsc.yaml ${TOPSAIL_DIR}/testing/watsonx-serving/poc/custom-manifests/opendatahub
