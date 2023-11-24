#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset
set -o errtrace
set -x

THIS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
source "$THIS_DIR/config.sh"

# scale
if [[ "$SCALE_INSTANCES" -eq 0 ]]
then
    ./run_toolbox.py cluster set-scale ${INSTANCE_TYPE} ${INSTANCE_COUNT}
fi

# run
for step in ${EXEC_LIST}
do
    if ! timeout $RUN_TIMEOUT bash ${THIS_DIR}/${step}; then
      echo "Step $step failed :/"
      break
    fi
done

# collect
for step in ${COLLECT_LIST}
do
    bash ${THIS_DIR}/${step}
done

