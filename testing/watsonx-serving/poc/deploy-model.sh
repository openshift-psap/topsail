#!/bin/bash

set -o pipefail
set -o errexit
set -o nounset
set -o errtrace
set -x

# Deploy a sample model

echo "Deploying the model ..."

TEST_NS=kserve-demo

oc create ns ${TEST_NS} -oyaml --dry-run=client | oc apply -f-

oc get smmr/default -n istio-system -ojson \
    | jq '.spec.members = (.spec.members + ["'$TEST_NS'"] | unique)' \
    | oc apply -f-

# ./custom-manifests/caikit/caikit-servingruntime.yaml
cat <<EOF | oc apply -f- -n ${TEST_NS}
apiVersion: serving.kserve.io/v1alpha1
kind: ServingRuntime
metadata:
  name: caikit-runtime
spec:
  containers:
  - env:
    - name: RUNTIME_LOCAL_MODELS_DIR
      value: /mnt/models
    image: quay.io/opendatahub/caikit-tgis-serving:stable-4d0134e
    name: kserve-container
    ports:
    # Note, KServe only allows a single port, this is the gRPC port. Subject to change in the future
    - containerPort: 8085
      name: h2c
      protocol: TCP
    resources:
      requests:
        cpu: 4
        memory: 8Gi
  multiModel: false
  supportedModelFormats:
  # Note: this currently *only* supports caikit format models
  - autoSelect: true
    name: caikit
EOF

oc get secret/storage-config -n minio -ojson \
    | jq 'del(.metadata.namespace) | del(.metadata.uid) | del(.metadata.creationTimestamp) | del(.metadata.resourceVersion)' \
    | oc apply -f- -n ${TEST_NS}

cat <<EOF | oc apply -f- -n ${TEST_NS}
apiVersion: v1
kind: ServiceAccount
metadata:
  name: sa
secrets:
- name: storage-config
EOF

# ./custom-manifests/caikit/caikit-isvc.yaml
cat <<EOF | oc apply -f- -n ${TEST_NS}
apiVersion: serving.kserve.io/v1beta1
kind: InferenceService
metadata:
  annotations:
    serving.knative.openshift.io/enablePassthrough: "true"
    sidecar.istio.io/inject: "true"
    sidecar.istio.io/rewriteAppHTTPProbers: "true"
  name: caikit-example-isvc
spec:
  predictor:
    serviceAccountName: sa
    model:
      modelFormat:
        name: caikit
      runtime: caikit-runtime
      storageUri: s3://modelmesh-example-models/llm/models
EOF

# Resources needed to enable metrics for the model
# The metrics service needs the correct label in the `matchLabel` field. The expected value of this label is `<isvc-name>-predictor-default`
# The metrics service in this repo is configured to work with the example model. If you are deploying a different model or using a different model name, change the label accordingly.

# custom-manifests/metrics/caikit-metrics-service.yaml
cat <<EOF | oc apply -f- -n ${TEST_NS}
kind: Service
apiVersion: v1
metadata:
  name: caikit-example-isvc-predictor-default-sm
  labels:
    name: caikit-example-isvc-predictor-default-sm
spec:
  ports:
    - name: caikit-metrics
      protocol: TCP
      port: 8086
      targetPort: 8086
  type: ClusterIP
  selector:
    serving.knative.dev/service: caikit-example-isvc-predictor-default
EOF

# custom-manifests/metrics/caikit-metrics-servicemonitor.yaml
cat <<EOF | oc apply -f- -n ${TEST_NS}
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: caikit-example-isvc-predictor-default-sm
spec:
  endpoints:
    - port: caikit-metrics
      scheme: http
  namespaceSelector: {}
  selector:
    matchLabels:
      name: caikit-example-isvc-predictor-default-sm
EOF
