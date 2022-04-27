#! /usr/bin/env bash

_info() {
    fname="$1"
    msg="$2"

    DEST_DIR="${ARTIFACT_DIR}/_INFO/"
    mkdir -p "$DEST_DIR"
    echo "$msg" > "${DEST_DIR}/$fname"

    echo "INFO: $msg"
}

_error() {
    fname="$1"
    msg="$2"

    DEST_DIR="${ARTIFACT_DIR}/_ERROR/"
    mkdir -p "$DEST_DIR"
    echo "$msg" > "${DEST_DIR}/$fname"

    echo "ERROR: $msg"
}

_warning() {
    fname="$1"
    msg="$2"

    DEST_DIR="${ARTIFACT_DIR}/_WARNING/"
    mkdir -p "$DEST_DIR"
    echo "$msg" > "${DEST_DIR}/$fname"

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

run_finalizers() {
    [ ${#finalizers[@]} -eq 0 ] && return
    set +x

    echo "Running exit finalizers ..."
    for finalizer in "${finalizers[@]}"
    do
        echo "Running finalizer '$finalizer' ..."
        eval $finalizer
    done
}

if [[ ! -v finalizers ]]; then
    finalizers=()
    trap run_finalizers EXIT
fi
