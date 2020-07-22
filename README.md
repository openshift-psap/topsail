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

Run a test

```bash
ansible-playbook -i inventory/hosts playbooks/openshift-ci.yml
```

## Ci playbook for the GPU operator

```bash
ansible-playbook -i inventory/hosts playbooks/nvidia-gpu-operator-ci.yml
```
