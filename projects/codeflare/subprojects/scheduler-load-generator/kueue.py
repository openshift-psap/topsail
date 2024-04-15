import copy

import config

def prepare_kueue_job(base_job, kueue_queue):
    kueue_job = copy.deepcopy(base_job)
    name = config.get_config("metadata.name", kueue_job)

    kueue_name = f"kueue-{name}"
    config.set_config(kueue_job, "metadata.name", kueue_name)

    kueue_job["spec"]["suspended"] = True
    kueue_job["metadata"]["labels"]["kueue.x-k8s.io/queue-name"] = kueue_queue

    return kueue_job,
