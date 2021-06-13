#!/bin/bash

set -euo pipefail

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")

if ! oc project -q; then
    echo 'Please select your project using "oc project" before running this script'
    exit 1
fi

set -x

oc apply -fhttps://raw.githubusercontent.com/openshift-psap/openshift-acme/passthrough/deploy/cluster-wide/{clusterrole,serviceaccount,issuer-letsencrypt-live,deployment}.yaml
oc create clusterrolebinding openshift-acme --clusterrole=openshift-acme --serviceaccount="$( oc project -q ):openshift-acme" --dry-run -o yaml | oc apply -f -
