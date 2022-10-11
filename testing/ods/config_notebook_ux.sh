RHODS_NOTEBOOK_IMAGE_NAME=s2i-generic-data-science-notebook

ODS_CI_TEST_NAMESPACE=loadtest
ODS_CI_REPO="https://github.com/openshift-psap/ods-ci.git"
ODS_CI_REF="jh-at-scale.v220923"

ODS_CI_IMAGESTREAM="ods-ci"
ODS_CI_TAG="latest"
ODS_CI_ARTIFACTS_EXPORTER_TAG="artifacts-exporter"
ODS_CI_ARTIFACTS_EXPORTER_DOCKERFILE="testing/ods/images/Containerfile.s3_artifacts_exporter"

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

# only taken into account if CUSTOMIZE_RHODS=1
# if value is 1, define a custom notebook size named $ODS_NOTEBOOK_SIZE
# see sutest_customize_rhods_after_wait for the limits/requests values
CUSTOMIZE_RHODS_USE_CUSTOM_NOTEBOOK_SIZE=1
ODS_NOTEBOOK_SIZE=Tiny # needs to match an existing notebook size in OdhDashboardConfig.spec.notebookSizes
ODS_NOTEBOOK_CPU_SIZE=1
ODS_NOTEBOOK_MEMORY_SIZE_GI=4

ODS_NOTEBOOK_BENCHMARK_NAME=pyperf_bm_go.py
ODS_NOTEBOOK_BENCHMARK_REPEAT=3
ODS_NOTEBOOK_BENCHMARK_NUMBER=20 # around 10s

ODS_NOTEBOOK_DIR=${THIS_DIR}/notebooks
ODS_EXCLUDE_TAGS=None # tags to exclude when running the robot test case

# number of test runs to perform
NOTEBOOK_TEST_RUNS=2

# name of the MatrixBenchmarking workload plugin to use for plotting
export MATBENCH_WORKLOAD=rhods-notebooks-ux

# if the value is different from 1, delete the test namespaces after the testing
CLEANUP_DRIVER_NAMESPACES_ON_EXIT=0
