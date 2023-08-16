#! /bin/bash

set -e

# based on https://github.com/opendatahub-io/caikit-tgis-serving/blob/8e9104109bb1bc79e57bc50933dc7363b73f5715/demo/kserve/Kserve.md
# and https://github.com/opendatahub-io/caikit-tgis-serving/blob/8e9104109bb1bc79e57bc50933dc7363b73f5715/demo/kserve/scripts/install/kserve-install.sh

GIT_REPO=Jooho/caikit-tgis-serving
GIT_REF=script-enhance

export TARGET_OPERATOR=brew # Set this among odh, rhods or brew, if you want to skip the question in the script.
export BREW_TAG=554196 # brew is a registry where WIP images are published. You need to ask the tag to use and it changes for every build
export CHECK_UWM=false # Set this to "false", if you want to skip the User Workload Configmap check message

# Enable User Workload Monitoring
# Configure User Workload Monitoring

cat <<EOF | oc apply -f-
apiVersion: v1
kind: ConfigMap
metadata:
  name: user-workload-monitoring-config
  namespace: openshift-user-workload-monitoring
data:
  config.yaml: |
    prometheus:
      logLevel: debug
      retention: 15d #Change as needed
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: cluster-monitoring-config
  namespace: openshift-monitoring
data:
  config.yaml: |
    enableUserWorkload: true
EOF

TOPSAIL_DIR=$(pwd)

rm -rf /tmp/caikit-tgis-serving /tmp/kserve

cd /tmp
git clone --quiet https://github.com/$GIT_REPO

cd caikit-tgis-serving/demo/kserve
git fetch --quiet origin "$GIT_REF"
git checkout FETCH_HEAD

git show --no-patch | tee $ARTIFACT_DIR/caikit-tgis-serving.commit

cp ${TOPSAIL_DIR}/testing/watsonx-serving/kserve-install.sh scripts/install/kserve-install.sh

bash -ex scripts/install/kserve-install.sh
bash -x scripts/test/deploy-model.sh
