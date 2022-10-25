#! /usr/bin/env bash

if [[ -z "${ARTIFACT_DIR:-}" ]]; then
    echo "ERROR: ARTIFACT_DIR must be defined ..."
    false
fi

_flake() {
    msg="$1"
    fname="${2:-msg}"

    DEST_DIR="${ARTIFACT_DIR}/_FLAKE/"
    mkdir -p "$DEST_DIR"
    echo "$msg" >> "${DEST_DIR}/$fname"

    echo "FLAKE: $msg"
}

_info() {
    msg="$1"
    fname="${2:-msg}"

    DEST_DIR="${ARTIFACT_DIR}/_INFO/"
    mkdir -p "$DEST_DIR"
    echo "$msg" >> "${DEST_DIR}/$fname"

    echo "INFO: $msg"
}

_error() {
    msg="$1"
    fname="${2:-msg}"

    DEST_DIR="${ARTIFACT_DIR}/_ERROR/"
    mkdir -p "$DEST_DIR"
    echo "$msg" >> "${DEST_DIR}/$fname"

    echo "ERROR: $msg"
    return 1
}

_warning() {
    msg="$1"
    fname="${2:-msg}"

    DEST_DIR="${ARTIFACT_DIR}/_WARNING/"
    mkdir -p "$DEST_DIR"
    echo "$msg" >> "${DEST_DIR}/$fname"

    echo "WARNING: $msg"
}

_expected_fail() {
    # mark the last toolbox step as an expected fail (for clearer
    # parsing/display in ci-dashboard)
    # eg: if cluster doesn't have NFD labels (expected fail), deploy NFD
    # eg: if cluster doesn't have GPU nodes (expected fail), scale up with GPU nodes

    last_toolbox_dir=$(ls ${ARTIFACT_DIR}/*__* -d | tail -1)
    echo "$1" > ${last_toolbox_dir}/EXPECTED_FAIL
}
