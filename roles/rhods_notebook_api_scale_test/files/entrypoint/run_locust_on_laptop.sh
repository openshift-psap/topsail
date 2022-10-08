#! /bin/bash

source ~/openshift/ci-artifacts/testing/ods/common.sh

export ODH_DASHBOARD_URL=https://$(oc get route -n redhat-ods-applications rhods-dashboard -ojsonpath={.spec.host})
export TEST_USERS_USERNAME_PREFIX=$LDAP_USER_PREFIX
export TEST_USERS_IDP_NAME=$LDAP_IDP_NAME
export CREDS_FILE=$S3_LDAP_PROPS
export NOTEBOOK_IMAGE_NAME=$RHODS_NOTEBOOK_IMAGE_NAME

export LOCUST_USERS=$ODS_CI_NB_USERS
export LOCUST_SPAWN_RATE=1
export LOCUST_RUN_TIME=5m
# or
#export LOCUST_ITERATIONS=1

export LOCUST_LOCUSTFILE=$PWD/locustfile.py

DEBUG_MODE=${DEBUG_MODE:-0}
if [[ "$DEBUG_MODE" == 1 ]]; then
    python3 "$LOCUST_LOCUSTFILE"
else
    mkdir -p results
    rm results/* -f

    locust --headless \
           --csv results/api_scale_test \
           --csv-full-history \
           --html results/api_scale_test.html \
           --only-summary

    locust-reporter \
        -prefix results/api_scale_test \
        -failures=true \
        -outfile results/locust_reporter.html
fi
