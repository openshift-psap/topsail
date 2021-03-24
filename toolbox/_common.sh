TOOLBOX_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
TOP_DIR=${TOOLBOX_DIR}/..

set -o pipefail
set -o errexit
set -o nounset

ANSIBLE_OPTS="${ANSIBLE_OPTS:--vv}"

### OpenShift version

if [ ! -z "${OCP_VERSION:-}" ]; then
    ANSIBLE_OPTS="$ANSIBLE_OPTS -e openshift_release=$OCP_VERSION"
fi

### Artifacts directory

if [ -z "${ARTIFACT_DIR:-}" ]; then
    export ARTIFACT_DIR="/tmp/ci-artifacts_$(date +%Y%m%d)"
    echo "Using '$ARTIFACT_DIR' to store the test artifacts (default value for ARTIFACT_DIR)."
else
    echo "Using '$ARTIFACT_DIR' to store the test artifacts."
fi


TOOLBOX_PATH="${0##*toolbox/}" # remove everything before 'toolbox/'
TOOLBOX_PATH="${TOOLBOX_PATH%.*}" # remove file extension
ARTIFACT_DIRNAME="${TOOLBOX_PATH//\//__}" # replace / by __
ARTIFACT_EXTRA_LOGS_DIR="${ARTIFACT_DIR}/$(date +%H%M%S)__${ARTIFACT_DIRNAME}" # add ARTIFACT_DIR/date__
export ARTIFACT_EXTRA_LOGS_DIR

mkdir -p "${ARTIFACT_EXTRA_LOGS_DIR}"
echo "Using '${ARTIFACT_EXTRA_LOGS_DIR}' to store extra log files."
ANSIBLE_OPTS="$ANSIBLE_OPTS -e artifact_extra_logs_dir=${ARTIFACT_EXTRA_LOGS_DIR}"

### Ansible logs  directory

if [ -z "${ANSIBLE_LOG_PATH:-}" ]; then
    export ANSIBLE_LOG_PATH="${ARTIFACT_EXTRA_LOGS_DIR}/_ansible_logs"
fi
echo "Using '${ANSIBLE_LOG_PATH}' to store ansible logs."
mkdir -p "$(dirname "${ANSIBLE_LOG_PATH}")"

# Ansible caching directory

if [ -z "${ANSIBLE_CACHE_PLUGIN_CONNECTION:-}" ]; then
    export ANSIBLE_CACHE_PLUGIN_CONNECTION="${ARTIFACT_EXTRA_LOGS_DIR}/ansible_facts"
fi
echo "Using '${ANSIBLE_CACHE_PLUGIN_CONNECTION}' to store ansible facts."
mkdir -p "${ANSIBLE_CACHE_PLUGIN_CONNECTION}"

# Ansible configuration file

if [ -z "${ANSIBLE_CONFIG:-}" ]; then
    export ANSIBLE_CONFIG="${TOP_DIR}/config/ansible.cfg"
fi
echo "Using '${ANSIBLE_CONFIG}' as ansible configuration file."

###

echo ""
cd $TOP_DIR
