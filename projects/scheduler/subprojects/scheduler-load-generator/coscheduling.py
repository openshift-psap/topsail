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
    namespace = config.get_config("metadata.namespace", new_job)
    kind = new_job["kind"]

    new_name = f"job-coscheduling-{name}"
    config.set_config(new_job, "metadata.name", new_name)
    if kind == "Job":
        config.set_config(new_job, "spec.template.spec.schedulerName", "coscheduling")
        config.set_config(new_job, "spec.template.metadata.labels['scheduling.x-k8s.io/pod-group']", new_name)
    elif kind == "PyTorchJob":
        config.set_config(new_job, "spec.pytorchReplicaSpecs.Master.template.spec.schedulerName", "coscheduling")
        config.set_config(new_job, "spec.pytorchReplicaSpecs.Master.template.metadata.labels['scheduling.x-k8s.io/pod-group']", new_name)

        config.set_config(new_job, "spec.pytorchReplicaSpecs.Worker.template.spec.schedulerName", "coscheduling")
        config.set_config(new_job, "spec.pytorchReplicaSpecs.Worker.template.metadata.labels['scheduling.x-k8s.io/pod-group']", new_name)
    else:
        raise ValueError(f"coscheduling: unsuported kind: {kind}")

    podgroup = yaml.safe_load(PODGROUP)
    config.set_config(podgroup, "metadata.name", new_name)
    config.set_config(podgroup, "metadata.namespace", namespace)

    if kind == "Job":
        config.set_config(podgroup, "spec.minMember", new_job["spec"]["parallelism"])

    elif kind == "PyTorchJob":
        worker_count = config.get_config("spec.pytorchReplicaSpecs.Worker.replicas", new_job)
        master_count = config.get_config("spec.pytorchReplicaSpecs.Master.replicas", new_job)
        config.set_config(podgroup, "spec.minMember", master_count + worker_count)

    return new_job, podgroup
