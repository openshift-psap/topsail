import sys
import logging
import copy

import config
import preparators.metadata

def prepare(namespace, job_template_name, base_name, pod_runtime, pod_requests, pod_count):

    job = preparators.metadata.prepare_base_job(namespace, job_template_name, base_name, pod_runtime)

    config.set_config(job, "spec.template.spec.containers[0].env[0].value", str(int(pod_runtime)))
    config.set_config(job, "spec.template.metadata.annotations.runtime", str(int(pod_runtime)))

    config.set_config(job, "spec.template.spec.containers[0].resources.limits", copy.deepcopy(pod_requests))
    config.set_config(job, "spec.template.spec.containers[0].resources.requests", copy.deepcopy(pod_requests))

    config.set_config(job, "spec.parallelism", int(pod_count))
    config.set_config(job, "spec.completions", int(pod_count))
    config.set_config(job, "spec.suspended", False)

    return job
