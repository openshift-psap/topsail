#! /bin/bash

set -o errexit
set -o pipefail
set -o nounset
set -o errtrace
set -x

THIS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
source "$THIS_DIR/config.sh"


function oc::wait::object::availability() {
    local cmd=$1 # Command whose output we require
    local interval=$2 # How many seconds to sleep between tries
    local iterations=$3 # How many times we attempt to run the command

    ii=0

    while [ $ii -le $iterations ]
    do

        token=$($cmd) && returncode=$? || returncode=$?
        if [ $returncode -eq 0 ]; then
            break
        fi

        ((ii=ii+1))
        if [ $ii -eq 100 ]; then
            echo $cmd "did not return a value"
            exit 1
        fi
        sleep $interval
    done
    echo $token
}

# Deploy ODH
./run_toolbox.py cluster deploy_operator community-operators opendatahub-operator all

# Deploy Model Mesh
oc create ns ${MODELMESH_PROJECT}
CWD=$(pwd)
cd /tmp
oc -n ${MODELMESH_PROJECT} apply -f $THIS_DIR/modelmesh.yaml
cd $CWD

echo "Waiting for kserve crds to be created by the Operator"
oc::wait::object::availability "oc -n ${MODELMESH_PROJECT} get crd inferenceservices.serving.kserve.io" 5 120
oc::wait::object::availability "oc -n ${MODELMESH_PROJECT} get crd predictors.serving.kserve.io" 5 120
oc::wait::object::availability "oc -n ${MODELMESH_PROJECT} get crd servingruntimes.serving.kserve.io" 5 120

