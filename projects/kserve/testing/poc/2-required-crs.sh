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
info "Let's create required CRs and required setup"

if [[ ! -d ${BASE_DIR} ]]
then
  mkdir ${BASE_DIR}
fi

if [[ ! -d ${BASE_CERT_DIR} ]]
then
  mkdir ${BASE_CERT_DIR}
fi

# kserve/knative
echo
light_info "[INFO] Update SMMR"
echo
oc::wait::object::availability "oc get project istio-system" 2 60
oc apply -f custom-manifests/service-mesh/default-smmr.yaml

# Create a Knative Serving installation
echo
light_info "[INFO] Wait for Knative Serving installation"
echo

wait_for_pods_ready "app=controller" "knative-serving"
wait_for_pods_ready "app=net-istio-controller" "knative-serving"
wait_for_pods_ready "app=net-istio-webhook" "knative-serving"
wait_for_pods_ready "app=autoscaler-hpa" "knative-serving"
wait_for_pods_ready "app=webhook" "knative-serving"
oc delete pod -n knative-serving -l app=activator --grace-period=0
oc delete pod -n knative-serving -l app=autoscaler --grace-period=0
wait_for_pods_ready "app=activator" "knative-serving"
wait_for_pods_ready "app=autoscaler" "knative-serving"

oc wait --for=condition=ready pod -l app=controller -n knative-serving --timeout=300s
oc wait --for=condition=ready pod -l app=net-istio-controller -n knative-serving --timeout=300s
oc wait --for=condition=ready pod -l app=net-istio-webhook -n knative-serving --timeout=300s
oc wait --for=condition=ready pod -l app=autoscaler-hpa -n knative-serving --timeout=300s
oc wait --for=condition=ready pod -l app=webhook -n knative-serving --timeout=300s
oc wait --for=condition=ready pod -l app=activator -n knative-serving --timeout=300s
oc wait --for=condition=ready pod -l app=autoscaler -n knative-serving --timeout=300s

success "[SUCCESS] Successfully created ServiceMesh Control Plane CR, KNative-Serving CR and required setup such as wildcard cert and Gateways"
