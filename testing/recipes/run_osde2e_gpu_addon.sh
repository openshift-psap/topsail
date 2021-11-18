#! /usr/bin/env bash

set -x
set -o pipefail
set -o errexit
set -o nounset

THIS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

PSAP_SECRET_PATH=/var/run/psap-entitlement-secret

source $THIS_DIR/../prow/gpu-operator.sh source

prepare_cluster_for_gpu_operator

./run_toolbox.py gpu_operator deploy_from_operatorhub --namespace openshift-operators

./testing/osde2e/gpu-addon.sh
