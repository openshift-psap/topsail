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
run gpu-ci             # test the GPU Operator from OperatorHub installation
run gpu-commit-ci      # test the GPU Operator from its `master` branch
run gpu-helm-ci 1.4.0  # test the GPU Operator from Helm installation
```

These commands will in-turn trigger `toolbox` commands, in order to
prepare the cluster, install the relevant operators and validate the
successful usage of the GPUs.

The `toolbox` commands are described in the section below.

## PSAP toolbox

See the progress and discussions about the toolbox development in
[this issue](https://github.com/openshift-psap/ci-artifacts/issues/34).

GPU Operator
------------

- [x] Deploy from OperatorHub
    - [ ] allow deploying an older version https://github.com/openshift-psap/ci-artifacts/issues/76
```
toolbox/gpu-operator/deploy_from_operatorhub.sh
toolbox/gpu-operator/undeploy_from_operatorhub.sh
```

- [x] Deploy from helm
```
toolbox/gpu-operator/list_version_from_helm.sh
toolbox/gpu-operator/deploy_with_helm.sh <helm-version>
toolbox/gpu-operator/undeploy_with_helm.sh
```

- [x]  Deploy from a custom commit.
```
toolbox/gpu-operator/deploy_from_commit.sh <git repository> <git reference> [gpu_operator_image_tag_uid]
Example:
toolbox/gpu-operator/deploy_from_commit.sh https://github.com/NVIDIA/gpu-operator.git master
```

- [x] Run the GPU Operator deployment validation tests
```
toolbox/gpu-operator/run_ci_checks.sh
```

- [x] Run GPU Burst to validate that all the GPUs of all the nodes can run workloads
```
toolbox/gpu-operator/run_gpu_burn.sh [gpu-burn runtime, in seconds]
```

- [ ] Capture GPU operator possible issues (entitlement, NFD labelling, operator deployment, state of resources in gpu-operator-resources, ...)
  - already partly done inside the CI, but we should improve the toolbox aspect


NFD
---

- [ ]  Deploy the NFD operator from OperatorHub:
```
toolbox/nfd/deploy_from_operatorhub.sh
toolbox/nfd/undeploy_from_operatorhub.sh
```
  - [ ]  Control the channel to use from the command-line

- [ ] Test the NFD deployment #78
  - [ ] test with the NFD if GPU nodes are available
  - [ ] wait with the NFD for GPU nodes to become available  #78
```
toolbox/nfd/has_gpu_nodes.sh
toolbox/nfd/wait_gpu_nodes.sh
```


Cluster
-------

- [x] Add a GPU node on AWS
```
./toolbox/scaleup_cluster.sh
```
   - [x] Specify a machine type in the command-line, and skip scale-up if a node with the given machine-type is already present
```
./toolbox/scaleup_cluster.sh <machine-type>
```

- [x] Entitle the cluster, by passing a PEM file, checking if they should be concatenated or not, etc. And do nothing is the cluster is already entitled
```
toolbox/entitlement/deploy.sh --pem /path/to/pem
toolbox/entitlement/deploy.sh --machine-configs /path/to/machineconfigs
toolbox/entitlement/undeploy.sh
toolbox/entitlement/test.sh
toolbox/entitlement/wait.sh
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
