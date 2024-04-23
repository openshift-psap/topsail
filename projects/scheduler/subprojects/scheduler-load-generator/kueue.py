import copy

import config

def prepare_kueue_job(base_job, kueue_queue):
    new_job = copy.deepcopy(base_job)
    name = config.get_config("metadata.name", new_job)
    kind = new_job["kind"]

    new_name = f"kueue-{name}"

    config.set_config(new_job, "metadata.name", new_name)

    new_job["metadata"]["labels"]["kueue.x-k8s.io/queue-name"] = kueue_queue

    if kind == "Job":
        config.set_config(new_job, "spec.suspended", True)
    elif kind == "PyTorchJob":
        config.set_config(new_job, "spec.runPolicy.suspended", True)
    else:
        raise ValueError(f"kueue: unsuported kind: {kind}")

    return new_job,
