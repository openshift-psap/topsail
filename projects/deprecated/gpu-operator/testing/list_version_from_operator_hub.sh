#! /bin/bash

NAMESPACE="${NAMESPACE:-openshift-marketplace}"
GRPCURL_IMAGE="docker.io/fullstorydev/grpcurl:v1.7.0"
QUERY_PODNAME="grpcurl-query"

DEFAULT_PACKAGE_NAME="gpu-operator-certified"
DEFAULT_CATALOG="certified-operators"
usage() {
    cat <<EOF
Usage:
  $0 [<package-name> [<catalog-name>]]
  $0 --help

Defaults:
  package-name: $DEFAULT_PACKAGE_NAME
  catalog-name: $DEFAULT_CATALOG
  namespace: $NAMESPACE (controlled with NAMESPACE environment variable)
EOF

}

if [ "${1:-}" ]; then
    if [ "$1" == "--help" ]; then
        usage
        exit 0
    fi
    PACKAGE_NAME="$1"
else
    PACKAGE_NAME="$DEFAULT_PACKAGE_NAME"
fi

if [ "${2:-}" ]; then
    CATALOG="$2"
else
    CATALOG="$DEFAULT_CATALOG"
fi

if ! oc get service/$CATALOG -oname -n $NAMESPACE > /dev/null; then
    echo "ERROR: catalog $CATALOG doesn't exist ..."
    echo "List of valid catalogs:"
    oc get services -oname -n $NAMESPACE | cut -d/ -f2
fi

CATALOG_SERVICE=$(oc get services/$CATALOG -n $NAMESPACE -oyaml)
CATALOG_IP=$(echo "${CATALOG_SERVICE}" | yq -r ".spec.clusterIP")
echo "Catalog ip: $CATALOG_IP" >&2
CATALOG_PORT=$(echo "${CATALOG_SERVICE}" | yq -r ".spec.ports[0].targetPort")
echo "Catalog port: $CATALOG_PORT" >&2

echo "Querying the catalog ..." >&2
oc delete pod/$QUERY_PODNAME -n $NAMESPACE >/dev/null 2>/dev/null

LIST_BUNDLES=$(oc run $QUERY_PODNAME  \
                  -n $NAMESPACE \
                  --quiet=true \
                  --rm=true \
                  --restart=Never \
                  --attach=true \
                  --image=$GRPCURL_IMAGE \
                  --  -plaintext "${CATALOG_IP}:${CATALOG_PORT}" api.Registry/ListBundles
            )
ret=$?
oc delete pod/$QUERY_PODNAME -n $NAMESPACE 2>/dev/null
if [ ! $ret == 0 ]; then
    echo "ERROR: failed to fetch the list of bundles">&2
    exit 1
fi

echo "Bundles for $PACKAGE_NAME:" >&2
echo "$LIST_BUNDLES" | jq -c 'select(.packageName=="'$PACKAGE_NAME'")|{packageName,channelName,csvName}'
