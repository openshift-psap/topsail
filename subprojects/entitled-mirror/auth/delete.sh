#!/bin/bash

set -euxo pipefail

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")

rm -f ${SCRIPT_DIR}/ca/generated*
rm -f ${SCRIPT_DIR}/client/generated*
