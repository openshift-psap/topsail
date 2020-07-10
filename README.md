# GPU-burst

> Performance & Latency Sensitive Application Platform 

GPU Node bursting automation for OpenShift
---

GPU-burst leverages OpenShift machine autoscaling API to burst GPU nodes

*WARNING* `This playbook as of today only works against AWS, more work is needed to add different cloud providers`

## Setup

The only thing that needs to be set is the instance type you want to scaleup at `inventory/<cloud-provider>/hosts`, default is set to `p3.2xlarge`(AWS Default GPU node)

After that run the playbook

```bash
ansible-playbook -i inventory/aws/hosts gpu-burst.yml
```

The playbook will wait until the machine state reports `Running` or report an error.
