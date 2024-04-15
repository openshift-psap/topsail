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

def prepare_coscheduling_job(base_job):
    new_job = copy.deepcopy(base_job)
    name = config.get_config("metadata.name", new_job)

    new_name = f"job-coscheduling-{name}"
    config.set_config(new_job, "metadata.name", new_name)
    new_job["spec"]["template"]["spec"]["schedulerName"] = "coscheduling"
    new_job["spec"]["template"]["metadata"]["labels"]["scheduling.x-k8s.io/pod-group"] = new_name

    podgroup = yaml.safe_load(PODGROUP)
    config.set_config(podgroup, "metadata.name", new_name)
    config.set_config(podgroup, "metadata.namespace", new_job["metadata"]["namespace"])
    config.set_config(podgroup, "spec.minMember", new_job["spec"].get("parallelism", 1))

    return new_job, podgroup
