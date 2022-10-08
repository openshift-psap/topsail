RHODS_NOTEBOOK_IMAGE_NAME=s2i-generic-data-science-notebook

ODS_CI_TEST_NAMESPACE=loadtest
ODS_CI_REPO="https://github.com/openshift-psap/ods-ci.git"
ODS_CI_REF="jh-at-scale.v220923"

ODS_CI_IMAGESTREAM="ods-ci"
ODS_CI_TAG="latest"
ODS_CI_ARTIFACTS_EXPORTER_TAG="artifacts-exporter"
ODS_CI_ARTIFACTS_EXPORTER_DOCKERFILE="testing/ods/images/Containerfile.s3_artifacts_exporter"

# if the value is different from 1, delete the test namespaces after the testing
CLEANUP_DRIVER_NAMESPACES_ON_EXIT=0

# must be consistent with roles/rhods_notebook_scale_test/templates/ods-ci_job.yaml

ODS_TESTPOD_CPU_SIZE=0.2
ODS_TESTPOD_MEMORY_SIZE_GI=0.75

ODS_CI_NB_USERS=5 # number of users to simulate
ODS_CI_USER_INDEX_OFFSET=0 # offset to add to the Pod user index

ODS_SLEEP_FACTOR=1.0 # how long to wait between user starts.
ODS_CI_ARTIFACTS_COLLECTED=no-image-except-failed-and-zero

STATESIGNAL_REDIS_NAMESPACE=loadtest-redis
NGINX_NOTEBOOK_NAMESPACE=loadtest-notebooks
ODS_NOTEBOOK_NAME=simple-notebook.ipynb

ODS_NOTEBOOK_BENCHMARK_NAME=pyperf_bm_go.py
ODS_NOTEBOOK_BENCHMARK_REPEAT=3
ODS_NOTEBOOK_BENCHMARK_NUMBER=20 # around 10s

ODS_NOTEBOOK_DIR=${THIS_DIR}/notebooks
ODS_EXCLUDE_TAGS=None # tags to exclude when running the robot test case

# number of test runs to perform
NOTEBOOK_TEST_RUNS=2

# if 1, the last test run will have only 1 user (for the notebook performance)
LAST_NOTEBOOK_TEST_RUN_IS_SINGLE=1
