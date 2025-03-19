import sys
import logging
import copy

import config
import preparators.kfjob

def prepare(namespace, job_template_name, base_name, pod_runtime, pod_requests, pod_count):

    return preparators.kfjob.prepare(namespace, job_template_name, base_name, pod_runtime, pod_requests, pod_count)
