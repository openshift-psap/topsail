# !/bin/bash

set -o pipefail
set -o errexit
set -o nounset
set -o errtrace
set -x

cd /mnt/app

echo "# configuration:"
cat "$CONFIG_JSON_PATH"

if python3 ./test_network_overhead.py; then
    echo "SCRIPT SUCCEEDED"
else
    echo "SCRIPT FAILED"
    # don't exit with a return code != 0, otherwise the RayJob->Job retries 3 times ...
fi
set +x
echo "*********"
echo "*********"
echo "*********"
echo "*********"
echo "********* Bye"
