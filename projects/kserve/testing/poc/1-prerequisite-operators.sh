#!/bin/bash
# Environment variables
# - CHECK_UWM: Set this to "false", if you want to skip the User Workload Configmap check message
# - TARGET_OPERATOR: Set this among odh, rhods or brew, if you want to skip the question in the script.

set -o pipefail
set -o errexit
set -o nounset
set -o errtrace
set -x

source "$(dirname "$(realpath "$0")")/../env.sh"
source "$(dirname "$(realpath "$0")")/../utils.sh"

echo
info "Let's install ServiceMesh, OpenDataHub and Serverless operators"

# Install Service Mesh operators
echo
light_info "[INFO] Install Service Mesh operators"
echo
# oc apply -f custom-manifests/service-mesh/operators.yaml

wait_for_csv_installed servicemeshoperator openshift-operators
oc wait --for=condition=ready pod -l name=istio-operator -n openshift-operators --timeout=300s

echo
light_info "[INFO] Install Serverless Operator"
echo
# oc apply -f custom-manifests/serverless/operators.yaml
# WARNING: we install the Serverless operator in namespace 'openshift-operators' instead of 'openshift-serverless'. The lines below must be updated accordingly.
wait_for_csv_installed serverless-operator openshift-operators

wait_for_pods_ready "name=knative-openshift" "openshift-operators"
wait_for_pods_ready "name=knative-openshift-ingress" "openshift-operators"
wait_for_pods_ready "name=knative-operator" "openshift-operators"
oc wait --for=condition=ready pod -l name=knative-openshift -n openshift-operators --timeout=300s
oc wait --for=condition=ready pod -l name=knative-openshift-ingress -n openshift-operators --timeout=300s
oc wait --for=condition=ready pod -l name=knative-operator -n openshift-operators --timeout=300s

success "[SUCCESS] Successfully installed ServiceMesh, Serverless operators"
