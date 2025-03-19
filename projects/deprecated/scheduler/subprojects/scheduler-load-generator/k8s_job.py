import copy
import logging

import config

def prepare_k8s_job(base_job):
    new_job = copy.deepcopy(base_job)
    name = config.get_config("metadata.name", new_job)

    new_name = f"job-standalone-{name}"
    config.set_config(new_job, "metadata.name", new_name)

    return new_job,
