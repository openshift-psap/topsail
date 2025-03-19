import sys
import logging
import copy

import config
import preparators.metadata

def prepare(namespace, job_template_name, base_name, pod_runtime, pod_requests, pod_count):

    kfjob = preparators.metadata.prepare_base_job(namespace, job_template_name, base_name, pod_runtime)

    config.set_config(kfjob, "spec.pytorchReplicaSpecs.Worker.replicas", int(pod_count))
    config.set_config(kfjob, "spec.pytorchReplicaSpecs.Worker..template.spec.containers[0].resources.limits", copy.deepcopy(pod_requests))
    config.set_config(kfjob, "spec.pytorchReplicaSpecs.Worker.template.spec.containers[0].resources.requests", copy.deepcopy(pod_requests))
    return kfjob
