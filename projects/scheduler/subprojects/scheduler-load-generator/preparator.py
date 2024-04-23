import sys
import logging

PREPARATORS = dict(
    sleeper = prepare_sleeper,
    training = prepare_training,
)

def prepare_training(namespace, job_template_name, base_name, pod_runtime, pod_requests, pod_count, kueue_mode):

    job_templates = config.get_config("job_templates")
    job_template = job_templates.get(job_template_name)

    if not job_template:
        logging.error(f"Could not find the requested job template '{job_template_name}'. Available names: {','.join(job_templates.keys())}")
        sys.exit(1)

    import pdb;pdb.set_trace()
    pass


def prepare_sleeper(namespace, job_template_name, base_name, pod_runtime, pod_requests, pod_count, kueue_mode):

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
    config.set_config(job, "spec.template.spec.containers[0].env[0].value", str(int(pod_runtime)))
    config.set_config(job, "spec.template.metadata.annotations.runtime", str(int(pod_runtime)))
    config.set_config(job, "spec.template.spec.containers[0].resources.limits", copy.deepcopy(pod_requests))
    config.set_config(job, "spec.template.spec.containers[0].resources.requests", copy.deepcopy(pod_requests))

    job["spec"]["parallelism"] = int(pod_count)
    job["spec"]["completions"] = int(pod_count)
    job["spec"]["suspended"] = False

    return job
