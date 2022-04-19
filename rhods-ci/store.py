import types
import pathlib
import yaml
import datetime

import matrix_benchmarking.store as store
import matrix_benchmarking.common as common

FMT = "%Y-%m-%dT%H:%M:%SZ"

def parse_execution_times(results, dirname):
    with open(dirname / "job.yaml") as f:
        job = yaml.safe_load(f)

    results.job_creation_time = \
        datetime.datetime.strptime(
            job["status"]["startTime"],
            FMT)
    results.job_completion_time = \
        datetime.datetime.strptime(
            job["status"]["completionTime"],
            FMT)

    with open(dirname / "pods.yaml") as f:
        podlist = yaml.safe_load(f)

    results.pod_time = {}
    for pod in podlist["items"]:
        podname = pod["metadata"]["name"]
        results.pod_time[podname] = types.SimpleNamespace()

        results.pod_time[podname].creation_time = \
            datetime.datetime.strptime(
                pod["metadata"]["creationTimestamp"],
                FMT)
        results.pod_time[podname].start_time = \
            datetime.datetime.strptime(
                pod["status"]["startTime"],
                FMT)

        if pod["status"]["containerStatuses"][0]["state"]["terminated"]:
            results.pod_time[podname].container_started = \
                datetime.datetime.strptime(
                    pod["status"]["containerStatuses"][0]["state"]["terminated"]["startedAt"],
                    FMT)

            results.pod_time[podname].container_finished = \
                datetime.datetime.strptime(
                    pod["status"]["containerStatuses"][0]["state"]["terminated"]["finishedAt"],
                    FMT)

        elif pod["status"]["containerStatuses"][0]["state"]["running"]:
            results.pod_time[podname].container_running_since = \
                datetime.datetime.strptime(
                    pod["status"]["containerStatuses"][0]["state"]["running"]["startedAt"],
                    FMT)

        else:
            import pdb;pdb.set_trace()

    pass

def parse_data(results_dir):
    settings = {"expe": "test", "value": "true"}
    results = types.SimpleNamespace()

    dirname = pathlib.Path(".") / "results"

    parse_execution_times(results, dirname)

    store.add_to_matrix(settings, None, results, None)
