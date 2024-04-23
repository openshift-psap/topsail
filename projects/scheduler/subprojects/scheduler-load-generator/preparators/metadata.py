import config
import logging
import sys
import copy

def prepare_base_job(namespace, job_template_name, base_name, pod_runtime):
    job_templates = config.get_config("job_templates")
    job_template = job_templates.get(job_template_name)

    if not job_template:
        logging.error(f"Could not find the requested job template '{job_template_name}'. Available names: {','.join(job_templates.keys())}")
        sys.exit(1)


    resource = copy.deepcopy(job_template)
    name = f"{base_name}-{{INDEX}}-{pod_runtime}s".replace("_", "-") # template name for create_appwrapper function

    config.set_config(resource, "metadata.name", name)
    config.set_config(resource, "metadata.namespace", namespace)
    config.set_config(resource, "metadata.annotations.scheduleTime", "{SCHEDULE-TIME}")

    return resource
