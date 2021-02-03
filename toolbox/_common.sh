TOOLBOX_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
TOP_DIR=${TOOLBOX_DIR}/..

set -o pipefail
set -o errexit
set -o nounset
set -x

ANSIBLE_OPTS="${ANSIBLE_OPTS:--vvv}"
INVENTORY_ARG="-i inventory/hosts"

cd $TOP_DIR
