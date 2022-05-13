#! /bin/bash

PR=360
EXPE_NAME=study

BASE_URL="https://gcsweb-ci.apps.ci.l2s4.p1.openshiftapps.com/gcs/origin-ci-test/pr-logs/pull/openshift-psap_ci-artifacts/$PR/pull-ci-openshift-psap-ci-artifacts-master-test-pr"
if [[ -n "${1:-}" ]]; then
    timestamp=$1
else
    timestamp=$(curl --silent "$BASE_URL/latest-build.txt")
fi

dt=$(date "+%F %H:%M" -d @$(echo "$timestamp" | cut -b-10))
dest="results/$EXPE_NAME/$timestamp"
if [[ -d "$dest" ]]; then
    echo "Destination '$dest' ($dt) already exists."
    exit 0
fi

echo "Download from PR #$PR: $dt"
mkdir "$dest"
cd "$dest"

results_url="$BASE_URL/$timestamp/artifacts/test-pr/test-pr/artifacts/ods_ci-1/004__rhods__test_jupyterlab"

for what in tester_pods.yaml tester_job.yaml tester_events.yaml notebook_events.yaml; do
  echo "Downloading $dest/$what ..."
  rm -f "$what"
  wget --quiet "$results_url/$what"
  cat <<EOF > settings
date=$dt
pr=$PR
EOF
  echo "0" > exit_code
done
