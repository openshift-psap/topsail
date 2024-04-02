import copy

import config

def prepare_base_job(namespace, job_template_name, base_name, pod_runtime, pod_requests, pod_count, kueue_mode):
    job_templates = config.get_config("job_templates")
    job_template = job_templates.get(job_template_name)

    if not job_template:
        logging.error(f"Could not find the requested job template '{job_template_name}'. Available names: {','.join(job_templates.keys())}")
        sys.exit(1)


    job = copy.deepcopy(job_template)
    job_name = f"{base_name}-{{INDEX}}-{pod_runtime}s".replace("_", "-") # template name for create_appwrapper function

    config.set_config(job, "metadata.name", job_name)
    config.set_config(job, "metadata.namespace", namespace)
    config.set_config(job, "metadata.annotations.scheduleTime", "{SCHEDULE-TIME}")
    config.set_config(job, "spec.template.spec.containers[0].env[0].value", str(pod_runtime))
    config.set_config(job, "spec.template.spec.containers[0].resources.limits", copy.deepcopy(pod_requests))
    config.set_config(job, "spec.template.spec.containers[0].resources.requests", copy.deepcopy(pod_requests))
    job["spec"]["suspended"] = False

    return job

def prepare_standalone_job(base_job):
    standalone_job = copy.deepcopy(base_job)
    name = config.get_config("metadata.name", standalone_job)

    standalone_name = f"job-standalone-{name}"
    config.set_config(standalone_job, "metadata.name", standalone_name)

    return standalone_job
