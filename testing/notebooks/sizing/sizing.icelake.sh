#! /bin/bash

set -o errexit
set -o pipefail
set -o nounset
set -o errtrace
set -x

TESTING_NOTEBOOKS_SIZING_DIR=$(dirname "$(realpath ${BASH_SOURCE[0]})")

source "$TESTING_NOTEBOOKS_SIZING_DIR/../configure.sh" # hardcoded values below could be replaced with $(get_config ...) commands ...

TEST_POD_NODES_LABEL_KEY=only-test-pods
TEST_POD_NODES_LABEL_VALUE=yes

NOTEBOOK_NODES_LABEL_KEY=only-rhods-compute-pods
NOTEBOOK_NODES_LABEL_VALUE=yes

MACHINE="Dell FC640"
MACHINE_LABEL_SELECTOR="-lfc640=yes"

USERS=1000

# test pods
TEST_POD_CPU=0.2
TEST_POD_MEM=0.750

NOTEBOOK_CPU=1.250
NOTEBOOK_MEM=4.160

"$TESTING_NOTEBOOKS_SIZING_DIR/sizing" "$MACHINE" "$USERS" "$TEST_POD_CPU" "$TEST_POD_MEM" || test_pod_node_count="$?"

echo "Preparing $test_pod_node_count test-pod nodes ..."

# notebooks

"$TESTING_NOTEBOOKS_SIZING_DIR/sizing" "$MACHINE" "$USERS" "$NOTEBOOK_CPU" "$NOTEBOOK_MEM" || notebook_node_count="$?"

echo "Preparing $notebook_node_count notebook nodes ..."

cluster_nodes=$(oc get nodes $MACHINE_LABEL_SELECTOR -oname)

if [[ $((test_pod_node_count + notebook_node_count)) -gt $(wc -l <<< $cluster_nodes) ]]; then
    echo "ERROR: need $notebook_node_count + $test_pod_node_count = $((test_pod_node_count + notebook_node_count)) '$MACHINE_LABEL_SELECTOR' nodes, found only $(wc -l <<< $cluster_nodes)."
    exit 1
fi

# ---

test_pod_nodes=$(head -$test_pod_node_count <<< $cluster_nodes)
notebook_nodes=$(tail -$notebook_node_count <<< $cluster_nodes)

## prepare the test nodes

# add test-pod annotations to the test nodes
oc label --overwrite $test_pod_nodes "${TEST_POD_NODES_LABEL_KEY}=${TEST_POD_NODES_LABEL_VALUE}" # add for test pods
oc adm taint nodes --overwrite $test_pod_nodes "$TEST_POD_NODES_LABEL_KEY=$TEST_POD_NODES_LABEL_VALUE:NoSchedule"

# remove notebook annotations from the test nodes
oc label $test_pod_nodes "${NOTEBOOK_NODES_LABEL_KEY}-" # remove for notebooks
oc adm taint nodes $test_pod_nodes "$NOTEBOOK_NODES_LABEL_KEY=$NOTEBOOK_NODES_LABEL_VALUE:NoSchedule-" || true

## prepare the notebook nodes

# add notebook annotations to the notebook nodes
oc label --overwrite $notebook_nodes "${NOTEBOOK_NODES_LABEL_KEY}=${NOTEBOOK_NODES_LABEL_VALUE}"
oc adm taint nodes --overwrite $notebook_nodes "$NOTEBOOK_NODES_LABEL_KEY=$NOTEBOOK_NODES_LABEL_VALUE:NoSchedule"

# remove test-pod annotations from the notebook nodes
oc label $notebook_nodes "${TEST_POD_NODES_LABEL_KEY}-"  # remove for test pods
oc adm taint nodes $notebook_nodes "$TEST_POD_NODES_LABEL_KEY=$TEST_POD_NODES_LABEL_VALUE:NoSchedule-" || true

## prepare the namespaces
exit 0
# configure the new projects
./run_toolbox.py from_config cluster set_project_annotation --prefix sutest --suffix node_selector
./run_toolbox.py from_config cluster set_project_annotation --prefix sutest --suffix toleration

# configure the rhods-notebooks project
./run_toolbox.py from_config cluster set_project_annotation --prefix sutest --suffix rhods_notebooks_node_selector
./run_toolbox.py from_config cluster set_project_annotation --prefix sutest --suffix rhods_notebooks_toleration

# configure the notebook-scale-test project
./run_toolbox.py from_config cluster set_project_annotation --prefix driver --suffix node_selector
./run_toolbox.py from_config cluster set_project_annotation --prefix driver --suffix toleration
