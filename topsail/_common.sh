TOOLBOX_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
TOP_DIR=${TOOLBOX_DIR}/..

set -o pipefail
set -o errexit
set -o nounset

ANSIBLE_OPTS="${ANSIBLE_OPTS:--vv}"

### OpenShift version

if [ "${OCP_VERSION:-}" ]; then
    ANSIBLE_OPTS="$ANSIBLE_OPTS -e openshift_release=$OCP_VERSION"
fi

### Artifacts directory

if [ -z "${ARTIFACT_DIR:-}" ]; then
    export ARTIFACT_DIR="/tmp/ci-artifacts_$(date +%Y%m%d)"
    echo "Using '$ARTIFACT_DIR' to store the test artifacts (default value for ARTIFACT_DIR)."
else
    echo "Using '$ARTIFACT_DIR' to store the test artifacts."
fi
ANSIBLE_OPTS="$ANSIBLE_OPTS -e artifact_dir=${ARTIFACT_DIR}"

TOOLBOX_SCRIPT_NAME="${TOOLBOX_SCRIPT_NAME:-$0}"
TOOLBOX_PATH="${TOOLBOX_SCRIPT_NAME##*topsail/}" # remove everything before 'topsail/'
TOOLBOX_PATH="${TOOLBOX_PATH%.*}" # remove file extension
ARTIFACT_DIRNAME="${TOOLBOX_PATH//\//__}" # replace / by __

mkdir -p "${ARTIFACT_DIR}"

if [ -z "${ARTIFACT_EXTRA_LOGS_DIR:-}" ]; then
    ARTIFACT_EXTRA_LOGS_DIR="${ARTIFACT_DIR}/$(printf '%03d' $(ls "${ARTIFACT_DIR}/" | grep __ | wc -l))__${ARTIFACT_DIRNAME}" # add ARTIFACT_DIR/date__
    export ARTIFACT_EXTRA_LOGS_DIR
fi

mkdir -p "${ARTIFACT_EXTRA_LOGS_DIR}"
echo "Using '${ARTIFACT_EXTRA_LOGS_DIR}' to store extra log files."
ANSIBLE_OPTS="$ANSIBLE_OPTS -e artifact_extra_logs_dir=${ARTIFACT_EXTRA_LOGS_DIR}"

### Ansible logs  directory

if [ -z "${ANSIBLE_LOG_PATH:-}" ]; then
    export ANSIBLE_LOG_PATH="${ARTIFACT_EXTRA_LOGS_DIR}/_ansible.log"
fi
echo "Using '${ANSIBLE_LOG_PATH}' to store ansible logs."
mkdir -p "$(dirname "${ANSIBLE_LOG_PATH}")"

# Ansible caching directory

if [ -z "${ANSIBLE_CACHE_PLUGIN_CONNECTION:-}" ]; then
    export ANSIBLE_CACHE_PLUGIN_CONNECTION="${ARTIFACT_DIR}/ansible_facts"
fi
echo "Using '${ANSIBLE_CACHE_PLUGIN_CONNECTION}' to store ansible facts."
mkdir -p "${ANSIBLE_CACHE_PLUGIN_CONNECTION}"

# Ansible configuration file

if [ -z "${ANSIBLE_CONFIG:-}" ]; then
    export ANSIBLE_CONFIG="${TOP_DIR}/config/ansible.cfg"
fi
echo "Using '${ANSIBLE_CONFIG}' as ansible configuration file."

# Custom Ansible JSON logging

if [ -z "${ANSIBLE_JSON_TO_LOGFILE:-}" ]; then
    export ANSIBLE_JSON_TO_LOGFILE="${ARTIFACT_EXTRA_LOGS_DIR}/_ansible.log.json"
fi

# export ANSIBLE_ROLES_PATH=$ANSIBLE_ROLES_PATH:$TOOLBOX_DIR/roles/benchmarking:$TOOLBOX_DIR/roles/fetch_external_test:$TOOLBOX_DIR/roles/cluster:$TOOLBOX_DIR/roles/codeflare:$TOOLBOX_DIR/roles/entitlement:$TOOLBOX_DIR/roles/gpu_operator:$TOOLBOX_DIR/roles/load_aware:$TOOLBOX_DIR/roles/local_ci:$TOOLBOX_DIR/roles/nfd:$TOOLBOX_DIR/roles/ocm:$TOOLBOX_DIR/roles/pipelines:$TOOLBOX_DIR/roles/rhods:$TOOLBOX_DIR/roles/utils:$TOOLBOX_DIR/roles/wisdom:$TOOLBOX_DIR/roles/watsonx_serving:$TOOLBOX_DIR/roles/llm_load_test:$TOOLBOX_DIR/roles/notebooks
# export ANSIBLE_COLLECTIONS_PATH=$ANSIBLE_COLLECTIONS_PATH:./ansible_collections:/usr/local/lib/python3.10/dist-packages/ansible_collections

echo "Using '${ANSIBLE_JSON_TO_LOGFILE}' as ansible json log file."

###

echo ""
cd $TOP_DIR
