#!/bin/sh

if ! [[ -d  $ARTIFACT_DIR ]] ; then
    echo "FATAL: osde2e tests requires '/test-run-results' to exist"
    exit 1
fi

BURN_RUNTIME_SEC=600

JUNIT_HEADER_TEMPLATE='<?xml version="1.0" encoding="utf-8"?>
<testsuite errors="NUM_ERRORS" failures="NUM_ERRORS" name="TEST_TARGET" tests="1" time="RUNTIME" timestamp="TIMESTAMP">
    <testcase name="TEST_TARGET" time="RUNTIME">
        <CASE_OUTPUT_TAG>
'

JUNIT_FOOTER_TEMPLATE='
        </CASE_OUTPUT_TAG>
    </testcase>
</testsuite>
'

function exit_and_abort() {
    echo "Failed. Aborting."
    exit 1
}

function run_test() {
    TARGET=${1:-}
    echo "====== Running toolbox '$TARGET'"
    JUNIT_FILE_NAME=$(echo $TARGET | awk '{print "junit_"$1"_"$2".xml"}')
    TARGET_NAME=$(echo $TARGET | sed 's/ /_/g')
    JUNIT_FILE="${ARTIFACT_DIR}/${JUNIT_FILE_NAME}"
    RUNTIME_FILE="${ARTIFACT_DIR}/runtime"
    OUTPUT_FILE="${ARTIFACT_DIR}/output"

    cat > ${JUNIT_FILE} <<EOF
$JUNIT_HEADER_TEMPLATE
EOF

    /usr/bin/time -o ${RUNTIME_FILE} ./run_toolbox.py ${TARGET} > $OUTPUT_FILE
    STATUS=$?

    cat $OUTPUT_FILE

    # Replace '<' and '>' from output so it won't break the XML
    sed  -i 's/[<>]/\*\*/g' $OUTPUT_FILE

    RUNTIME="$(cat ${RUNTIME_FILE} | egrep -o '[0-9]+:[0-9]+\.[0-9]+elapsed' | sed 's/elapsed//')"

    sed -i "s/RUNTIME/${RUNTIME}/g" "${JUNIT_FILE}"
    sed -i "s/TEST_TARGET/${TARGET_NAME}/g" "${JUNIT_FILE}"
    sed -i "s/TIMESTAMP/$(date -Is)/g" "${JUNIT_FILE}"

    cat $OUTPUT_FILE >> $JUNIT_FILE
    cat >> "${JUNIT_FILE}" <<EOF  
    $JUNIT_FOOTER_TEMPLATE
EOF

    rm -rf ${RUNTIME_FILE}
    rm -rf ${OUTPUT_FILE}

    if [[ $STATUS == 0 ]]; then
        sed -i 's/NUM_ERRORS/0/g' "${JUNIT_FILE}"
        sed -i 's/CASE_OUTPUT_TAG/system-out/g' "${JUNIT_FILE}"
    else
        sed -i 's/NUM_ERRORS/1/g' "${JUNIT_FILE}"
        sed -i 's/CASE_OUTPUT_TAG/failure/g' "${JUNIT_FILE}"
        exit_and_abort
    fi
}


echo "====== Starting OSDE2E tests..."

echo "Using ARTIFACT_DIR=$ARTIFACT_DIR."

echo "====== waiting for gpu-operator..."
run_test "gpu_operator wait_deployment"
echo "====== Operator found."

echo "====== Running burn test for $((BURN_RUNTIME_SEC/60)) minutes ..."
run_test "gpu_operator run_gpu_burn --runtime=${BURN_RUNTIME_SEC}"
echo "====== Done."
