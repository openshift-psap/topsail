#! /bin/bash

THIS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
source ${THIS_DIR}/../_common.sh

source ${THIS_DIR}/_helm_common.sh

exec bash -x "${HELM_DEPLOY_OPERATOR}" undeploy
