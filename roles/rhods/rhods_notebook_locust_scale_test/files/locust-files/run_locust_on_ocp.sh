#! /bin/bash

THIS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$(realpath $THIS_DIR)/../../../.."
source testing/notebooks/configure.sh
exec ./run_toolbox.py from_config rhods notebook_locust_scale_test
