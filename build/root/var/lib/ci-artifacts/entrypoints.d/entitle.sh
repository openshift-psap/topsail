#! /usr/bin/env bash

set -o pipefail
set -o errexit
set -o nounset

entitle() {
    echo "Testing if the cluster is already entitled ..."
    if toolbox/entitlement/test.sh --no-inspect; then
        echo "Cluster already entitled, skipping entitlement."
        return
    fi

    entitlement_deployed=0

    ENTITLEMENT_PEM=${ENTITLEMENT_PEM:-/var/run/psap-entitlement-secret/entitlement.pem}
    if [ -z "$ENTITLEMENT_PEM" ]; then
        echo "INFO: no entitlement key provided (ENTITLEMENT_PEM)"
    elif [ ! -e "$ENTITLEMENT_PEM" ]; then
        echo "INFO: entitlement key doesn't exist (ENTITLEMENT_PEM=$ENTITLEMENT_PEM)"
    else
        echo "Deploying the entitlement with PEM key from ${ENTITLEMENT_PEM}"
        toolbox/entitlement/deploy.sh --pem ${ENTITLEMENT_PEM}
        entitlement_deployed=1
    fi

    ENTITLEMENT_RESOURCES=${ENTITLEMENT_RESOURCES:-/var/run/psap-entitlement-secret/01-cluster-wide-machineconfigs.yaml}
    if [ "$entitlement_deployed" == 1 ]; then
        # entitlement already deployed
        true
    elif [ -z "$ENTITLEMENT_RESOURCES" ]; then
        echo "INFO: no entitlement resource provided (ENTITLEMENT_RESOURCES)"
    elif [ ! -e "$ENTITLEMENT_RESOURCES" ]; then
        echo "INFO: entitlement resource file doesn't exist (ENTITLEMENT_RESOURCES=$ENTITLEMENT_RESOURCES)"
     else
        echo "Deploying the entitlement from resources inside ${ENTITLEMENT_RESOURCES}"
        toolbox/entitlement/deploy.sh --machine-configs ${ENTITLEMENT_RESOURCES}
        entitlement_deployed=1
    fi


    if [ "$entitlement_deployed" == 0 ]; then
        echo "FATAL: cluster isn't entitled and not entitlement provided (ENTITLEMENT_PEM)"
        exit 1
    fi

    if ! toolbox/entitlement/wait.sh; then
        echo "FATAL: Failed to properly entitle the cluster, cannot continue."
        exit 1
    fi
}
