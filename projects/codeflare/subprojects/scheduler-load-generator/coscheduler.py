import copy
import logging
import yaml

import config, k8s_quantity

PODGROUP = """
# PodGroup CRD spec
apiVersion: scheduling.x-k8s.io/v1alpha1
kind: PodGroup
metadata:
  name: ...
  namespace: ...
spec:
  minMember: ...
"""

def prepare_coscheduler_job(base_job):
    coscheduler_job = copy.deepcopy(base_job)
    name = config.get_config("metadata.name", coscheduler_job)

    coscheduler_name = f"job-coscheduler-{name}"
    config.set_config(coscheduler_job, "metadata.name", coscheduler_name)
    coscheduler_job["spec"]["template"]["spec"]["schedulerName"] = "coscheduler"
    coscheduler_job["spec"]["template"]["metadata"]["labels"]["scheduling.x-k8s.io/pod-group"] = coscheduler_name

    podgroup = yaml.safe_load(PODGROUP)
    config.set_config(podgroup, "metadata.name", coscheduler_name)
    config.set_config(podgroup, "metadata.namespace", coscheduler_job["metadata"]["namespace"])
    config.set_config(podgroup, "spec.minMember", coscheduler_job["spec"].get("parallelism", 1))

    return coscheduler_job, podgroup
