import sys
import logging
import copy

import config
import preparators.job

def prepare(namespace, job_template_name, base_name, pod_runtime, pod_requests, pod_count):

    return preparators.job.prepare(namespace, job_template_name, base_name, pod_runtime, pod_requests, pod_count)
