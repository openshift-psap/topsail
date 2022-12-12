#! /usr/bin/env bash

if [[ -z "${ARTIFACT_DIR:-}" ]]; then
    echo "$0: WARNING: ARTIFACT_DIR not defined ..."
fi

_flake() {
    __do_log FLAKE "$@"
}

_info() {
    __do_log INFO "$@"
}

_error() {
    __do_log ERROR "$@"

    return 1
}

_warning() {
    __do_log WARNING "$@"
}

_expected_fail() {
    # mark the last toolbox step as an expected fail (for clearer
    # parsing/display in ci-dashboard)
    # eg: if cluster doesn't have NFD labels (expected fail), deploy NFD
    # eg: if cluster doesn't have GPU nodes (expected fail), scale up with GPU nodes

    last_toolbox_dir=$(ls ${ARTIFACT_DIR}/*__* -d | tail -1)
    echo "$1" > ${last_toolbox_dir}/EXPECTED_FAIL
}

__do_log() {
    level=$1
    shift
    msg="$1"
    shift
    fname="${1:-msg}"

    echo "${level}: $msg"

    if [[ -z "${ARTIFACT_DIR:-}" ]]; then
        return
    fi

    DEST_DIR="${ARTIFACT_DIR}/_${level}/"
    mkdir -p "$DEST_DIR"
    echo "$msg" >> "${DEST_DIR}/$fname"
}
