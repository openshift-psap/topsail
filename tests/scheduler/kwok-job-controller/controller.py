import logging
import asyncio

import kopf
import kubernetes

import jsonpath_ng


NODE_NAME = "kwok-machine-0"

known_pods = []

def yaml_get(obj, key, missing=...):
    jsonpath_expression = jsonpath_ng.parse(f'$.{key}')
    match = jsonpath_expression.find(obj)
    if not match:
        if missing != ...:
            return missing

        raise KeyError(f"Key '{key}' not found  ...")

    return match[0].value


def on_end_of_run_timer(pod):
    # apply label metadata.labels.complete=yes
    pass


def api_mark_pod_as_state(logger, pod_name, namespace, state):
    logging.info(f"Marking {pod_name} as {state.title()}")
    logger.info(f"Marking Pod as {state.title()}")

    body = {
        "metadata": {
            "labels": {state: "yes"},
            "annotations": {state: "NOW"},
        }
    }

    api = kubernetes.client.CoreV1Api()
    api_response = api.patch_namespaced_pod(pod_name, namespace, body)

    pass


def ctrl_check_job_ready(meta, namespace):
    pod_name = yaml_get(meta, "name")
    job_name = yaml_get(meta, "ownerReferences[0].name")

    api = kubernetes.client.BatchV1Api()
    job = api.read_namespaced_job(
        job_name, namespace
    )

    total = job.spec.completions
    active = job.status.active

    if active != total:
        logging.info(f"Job {job_name} has only {active}/{total} active Pods")
        return False

    return True


async def ctrl_wait_pod_runtime(logger, meta):
    pod_name = meta["name"]
    pod_runtime = int(meta["annotations"]["runtime"])

    logging.info(f"Waiting {pod_runtime}s for Pod {pod_name}")
    logger.info(f"Waiting {pod_runtime}s to simulate execution ...")

    await asyncio.sleep(pod_runtime)

    logging.info(f"Waiting completed for Pod {pod_name}")
    logger.info(f"Waiting {pod_runtime}s completed")


@kopf.on.update('pod') # field='spec.nodeName', value=NODE_NAME
async def pod_update(logger, param, retry, started, runtime, memo, resource, patch, body, reason, diff, old, new, spec, meta, status, uid, name, namespace, labels, annotations):

    pod_name = yaml_get(meta, "name")

    is_ready = labels.get("ready", False) == "yes"
    is_complete = labels.get("complete", False) == "yes"

    if is_complete:
        logging.warning(f"{name}: complete, nothing to do")
        return # nothing to do, Pod is done

    if is_ready:
        logging.warning(f"{name}: ready, nothing to do")
        return

    logging.warning(f"{name}: not ready")

    if not ctrl_check_job_ready(meta, namespace):
        logging.warning(f"{name}: job not ready")
        return

    api_mark_pod_as_state(logger, pod_name, namespace, state="ready")
    await ctrl_wait_pod_runtime(logger, meta)
    api_mark_pod_as_state(logger, pod_name, namespace, state="complete")
