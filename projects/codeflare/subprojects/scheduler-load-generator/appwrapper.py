import yaml
import pathlib
import logging
import copy
import json
import datetime

import config


def prepare_appwrapper(namespace, job, priority, pod_count, pod_requests):
    with open(pathlib.Path(__file__).parent / "base_appwrapper.yaml") as f:
        appwrapper = yaml.safe_load(f)

    job_name = config.get_config("metadata.name", job)
    appwrapper_name = f"aw-{job_name}"
    config.set_config(appwrapper, "metadata.name", appwrapper_name)
    config.set_config(appwrapper, "metadata.annotations.scheduleTime", "{SCHEDULE-TIME}")

    aw_genericitems = [dict(
        replicas = 1,
        completionstatus = "Complete",
        custompodresources=[dict(
            replicas=1,
            requests=copy.deepcopy(pod_requests),
            limits=copy.deepcopy(pod_requests),
        )],
        generictemplate = job,
    )]

    config.set_config(appwrapper, "spec.resources.GenericItems", aw_genericitems)
    config.set_config(appwrapper, "metadata.namespace", namespace)
    config.set_config(appwrapper, "spec.priority", priority)

    return appwrapper
