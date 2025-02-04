import sys
import logging
import copy
import pathlib
import yaml, json

import config
import preparators.metadata

def prepare(namespace, job_template_name, base_name, pod_runtime, pod_requests, pod_count):
    job_template_name_file = pathlib.Path(job_template_name)

    with open(job_template_name_file) as f:
        if job_template_name_file.suffix == ".yaml":
            resource = yaml.safe_load(f)
        elif job_template_name_file.suffix == ".json":
            resource = json.load(f)
        else:
            raise ValueError(f"Cannot open {job_template_name_file}. Unknown type ...")

    name = f"{base_name}-{{INDEX}}".replace("_", "-") # template name for utils.create_resource function
    config.set_config(resource, "metadata.name", name)
    config.set_config(resource, "metadata.namespace", namespace)

    if "labels" not in resource["metadata"]:
        config.set_config(resource, "metadata.labels", {})

    return resource
