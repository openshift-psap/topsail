#! /bin/bash

PR=360

BASE_URL="https://gcsweb-ci.apps.ci.l2s4.p1.openshiftapps.com/gcs/origin-ci-test/pr-logs/pull/openshift-psap_ci-artifacts/$PR/pull-ci-openshift-psap-ci-artifacts-master-test-pr"
timestamp=$(curl --silent "$BASE_URL/latest-build.txt")
results_url="$BASE_URL/$timestamp/artifacts/test-pr/test-pr/artifacts/ods_ci-1/004__rhods__test_jupyterlab"

cd results
for what in tester_pods.yaml tester_job.yaml tester_events.yaml notebook_events.yaml; do
  echo "Downloading $what ..."
  rm -f "$what"
  wget --quiet "$results_url/$what" 
done
