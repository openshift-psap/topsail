import copy
import logging

import config, k8s_quantity

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
    job["spec"]["parallelism"] = pod_count
    job["spec"]["completions"] = pod_count
    job["spec"]["suspended"] = False

    return job

def prepare_standalone_job(base_job):
    standalone_job = copy.deepcopy(base_job)
    name = config.get_config("metadata.name", standalone_job)

    standalone_name = f"job-standalone-{name}"
    config.set_config(standalone_job, "metadata.name", standalone_name)

    # pod_count = standalone_job["spec"].get("parallelism", 1)
    # if pod_count != 1:
    #     logging.info(f"prepare_standalone_job: {pod_count} are requests. Turn the resource requests into a single request.")
    #     standalone_job["spec"]["parallelism"] = 1
    #     standalone_job["spec"]["completions"] = 1

    #     requests = standalone_job["spec"]["template"]["spec"]["containers"][0]["resources"]["requests"]
    #     for k, v in requests.items():
    #         qte = k8s_quantity.parse_quantity(v)
    #         requests[k] = str(qte * pod_count)

    #     limits = standalone_job["spec"]["template"]["spec"]["containers"][0]["resources"]["limits"]
    #     for k, v in limits.items():
    #         qte = k8s_quantity.parse_quantity(v)
    #         limits[k] = str(qte * pod_count)

    return standalone_job
