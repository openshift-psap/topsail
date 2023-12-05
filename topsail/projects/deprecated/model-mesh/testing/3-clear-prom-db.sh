#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset
set -o errtrace
set -x

./run_toolbox.py cluster reset_prometheus_db

