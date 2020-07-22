# OpenShift-PSAP Ci Artifacs

This repository contains [Ansible](https://www.ansible.com/) roles and
playbooks for [OpenShift](https://www.openshift.com/) PSAP Ci.

> Performance & Latency Sensitive Application Platform 

---

# Quickstart

Requirements: (localhost)

- Ansible >= 2.9.5
- OpenShift Client (oc)
- kubeconfig file defined at KUBECONFIG

## Ci playbook for the NFD  operator

Ci run for NFD, deploys NFD from git, and check the health of the operator

TODO: deploy from OperatorHub

```bash
ansible-playbook -i inventory/hosts playbooks/openshift-ci.yml
```

## Ci playbook for the GPU operator

Ci run for the GPU operator

[Optional] In case of not having a GPU ready OpenShift node, run this playbook first

```bash
ansible-playbook -i inventory/hosts playbooks/gpu-burst.yml
```

With an openShift GPU ready node, we can then run

```bash
ansible-playbook -i inventory/hosts playbooks/nvidia-gpu-operator-ci.yml
```
