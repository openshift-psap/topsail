#! /bin/bash -e

THIS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

if [[ -z "${1:-}" || -z "${2:-}" || "${3:---force}" != "--force" ]]; then
    echo "USAGE: ${0} <instance_type> <scale> [--force]"
    echo "
AWS instance information:
We typically use the g4dn.xlarge instance type as a cheap GPU node.
By default, on AWS, the OCS installer usually uses m4.large, which does not have a GPU.
For a list of AWS instance types see https://aws.amazon.com/ec2/instance-types/.
More specifically, check the 'Accelerated Computing' section for instances with GPU

scale is the total amount (across all machinesets of given instance type) of replicas to set.

If the machinesets of the given instance type already have the required total number of replicas,
their replica parameters will not be modified.

Otherwise,
- If there's only one machineset with the given instance type, its replicas will be set to the value of this parameter.

- If there are other machinesets with non-zero replicas, the playbook will fail, unless the 'force_scale' parameter is
set to true. In that case, the number of replicas of the other machinesets will be zeroed before setting the replicas
of the first machineset to the value of this parameter."

    exit 1
fi

source ${THIS_DIR}/../_common.sh

INSTANCE_TYPE=${1}
ANSIBLE_OPTS="${ANSIBLE_OPTS} -e machineset_instance_type=${INSTANCE_TYPE}"

shift

echo "Setting cluster ${INSTANCE_TYPE} machinesets to have scale '${1}'"
ANSIBLE_OPTS="${ANSIBLE_OPTS} -e scale=${1}"

shift

if [ "${1-}" == "--force" ]; then
    echo "Setting cluster ${INSTANCE_TYPE} machinesets to have scale '${1}'"
    ANSIBLE_OPTS="${ANSIBLE_OPTS} -e force_scale=true"
fi

exec ansible-playbook ${ANSIBLE_OPTS} playbooks/cluster_set_scale.yml
