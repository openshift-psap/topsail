TOOLBOX_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
TOP_DIR=${TOOLBOX_DIR}/..

set -o pipefail
set -o errexit
set -o nounset

ANSIBLE_OPTS="${ANSIBLE_OPTS:--vv}"
INVENTORY_ARG="-i inventory/hosts"

if [ ! -z "${OCP_VERSION:-}" ]; then
    ANSIBLE_OPTS="$ANSIBLE_OPTS -e openshift_release=$OCP_VERSION"
fi

export ANSIBLE_CACHE_PLUGIN_CONNECTION="${ANSIBLE_CACHE_PLUGIN_CONNECTION:-/tmp/ansible/facts}"
echo "Using ${ANSIBLE_CACHE_PLUGIN_CONNECTION} for storing ansible facts."

cd $TOP_DIR
