#!/bin/bash

set -euo pipefail

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")

if [[ ${NAMESPACE:-} == "" ]]; then
    echo Please source a mirror configuration file before running this script
    exit 1
fi

set -x

oc new-project $NAMESPACE || true
oc project $NAMESPACE

oc apply -fhttps://raw.githubusercontent.com/openshift-psap/openshift-acme/passthrough/deploy/single-namespace/{role,serviceaccount,issuer-letsencrypt-live,deployment}.yaml
oc create rolebinding openshift-acme --role=openshift-acme --serviceaccount="$( oc project -q ):openshift-acme" --dry-run=client -o yaml | oc apply -f -
