# OpenShift-PSAP CI Artifacs

This repository contains [Ansible](https://www.ansible.com/) roles and
playbooks for [OpenShift](https://www.openshift.com/) PSAP CI.

> Performance & Latency Sensitive Application Platform

---

# Quickstart

Requirements: (localhost)

- Ansible >= 2.9.5
- OpenShift Client (`oc`)
- A kubeconfig config file defined at `KUBECONFIG`

# CI testing of the GPU Operator

The main goal of this repository is to perform nightly testing of the
GPU Operator. This consists in multiple pieces:

1. a container image [definition](build/Dockerfile);
2. an [entrypoint script](for the container image) that will run in
the container image;
3. a set of
[config files](https://github.com/openshift/release/tree/master/ci-operator/config/openshift-psap/ci-artifacts)
and associated
[jobs](https://github.com/openshift/release/tree/master/ci-operator/jobs/openshift-psap/ci-artifacts)
for PROW CI engine.

See
[there](https://prow.ci.openshift.org/?type=periodic&job=periodic-ci-openshift-psap-ci-artifacts-*)
for the nightly CI results.

As an example, the nightly tests currently run commands such as:

```
run gpu-operator_test-operatorhub    # test the GPU Operator from OperatorHub installation
run gpu-operator_test-master-branch  # test the GPU Operator from its `master` branch
run gpu-operator_test-helm 1.4.0     # test the GPU Operator from Helm installation
```

These commands will in-turn trigger `toolbox` commands, in order to
prepare the cluster, install the relevant operators and validate the
successful usage of the GPUs.

The `toolbox` commands are described in the section below.

## GPU Operator toolbox

See the progress and discussions about the toolbox development in
[this issue](https://github.com/openshift-psap/ci-artifacts/issues/34).


Cluster
-------

- [x] Set number of nodes with given instance type on AWS
```
./toolbox/cluster/set_scale.sh <machine-type> <replicas>

Example usage:
# Set the total number of g4dn.xlarge nodes to 2
./toolbox/cluster/set_scale.sh g4dn.xlarge 2

# Set the total number of g4dn.xlarge nodes to 5,
# even when there are some machinesets that might need to be downscaled
# to 0 to achive that.
./toolbox/cluster/set_scale.sh g4dn.xlarge 5 --force
```

- [x] Entitle the cluster with a PEM file, check if the key is working properly or not...
```
toolbox/entitlement/deploy.sh --pem /path/to/key.pem
toolbox/entitlement/undeploy.sh
toolbox/entitlement/test.sh [--no-inspect]
toolbox/entitlement/wait.sh

toolbox/entitlement/test_in_podman.sh /path/to/key.pem
toolbox/entitlement/test_in_cluster.sh /path/to/key.pem
```
  - [x] Capture all the clues required to understand entitlement issues

```
toolbox/entitlement/inspect.sh
```

- [ ] Deployment of an entitled cluster
  - already coded, but we need to integrate [this repo](https://gitlab.com/kpouget_psap/deploy-cluster) within the toolbox
  - deploy a cluster with 1 master node

CI
---

- [x] Build the image used for the Prow CI testing, and run a given command in the Pod
```
Usage:   toolbox/local-ci/deploy.sh <ci command> <git repository> <git reference> [gpu_operator_image_tag_uid]
Example: toolbox/local-ci/deploy.sh 'run gpu-ci' https://github.com/openshift-psap/ci-artifacts.git master

toolbox/local-ci/cleanup.sh
```
