
OCM_ENV=staging # The valid aliases are 'production', 'staging', 'integration'

# If the value is set, consider SUTEST to be running on OSD or ROSA,
# and use this cluster name to configure LDAP and RHODS
# Note:
# * KEEP EMPTY IF SUTEST IS NOT ON OSD
# * KEEP EMPTY ON CI, OSD OR OCP ALIKE
OSD_CLUSTER_NAME=

# If the value is set, consider SUTEST to be running on ROSA
# * KEEP EMPTY ON CI
OSD_CLUSTER_IS_ROSA=

CLUSTER_NAME_PREFIX=odsci

OSD_VERSION=4.10.15
OSD_REGION=us-west-2

OSD_WORKER_NODES_TYPE=m6.xlarge
OSD_WORKER_NODES_COUNT=3

OCP_VERSION=4.10.15
OCP_REGION=us-west-2
OCP_MASTER_MACHINE_TYPE=m6a.xlarge
OCP_INFRA_MACHINE_TYPE=m6a.xlarge
OCP_INFRA_NODES_COUNT=2

OCP_BASE_DOMAIN=psap.aws.rhperfscale.org

# if not empty, enables auto-scaling in the sutest cluster
SUTEST_ENABLE_AUTOSCALER=

SUTEST_MACHINESET_NAME=rhods-compute-pods
SUTEST_TAINT_KEY=only-$SUTEST_MACHINESET_NAME
SUTEST_TAINT_VALUE=yes
SUTEST_TAINT_EFFECT=NoSchedule
SUTEST_NODE_SELECTOR="$SUTEST_TAINT_KEY: '$SUTEST_TAINT_VALUE'"

DRIVER_MACHINESET_NAME=test-pods
DRIVER_TAINT_KEY=only-$DRIVER_MACHINESET_NAME
DRIVER_TAINT_VALUE=yes
DRIVER_TAINT_EFFECT=NoSchedule
DRIVER_NODE_SELECTOR="$DRIVER_TAINT_KEY: '$DRIVER_TAINT_VALUE'"

DRIVER_COMPUTE_MACHINE_TYPE=m5a.2xlarge
OSD_SUTEST_COMPUTE_MACHINE_TYPE=m5.2xlarge
OCP_SUTEST_COMPUTE_MACHINE_TYPE=m5a.2xlarge

SUTEST_FORCE_COMPUTE_NODES_COUNT= # if empty, uses ods/sizing/sizing to determine the right number of machines
DRIVER_FORCE_COMPUTE_NODES_COUNT= # if empty, uses ods/sizing/sizing to determine the right number of machines

# OSP/OSD cluster naming is handled differently in this job
JOB_NAME_SAFE_GET_CLUSTER_SUFFIX="get-cluster"

# cluster that will be available right away when going to the debug tab of the test pod in the CI cluster
CI_DEFAULT_CLUSTER=driver

# number of hours CI clusters are allowed to stay alive, before we clean them up
CLUSTER_CLEANUP_DELAY=4

# value can be single, ocp, osd
CI_DEFAULT_CLUSTER_TYPE=single
