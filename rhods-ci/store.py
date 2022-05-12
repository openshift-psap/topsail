import types
import pathlib
import yaml
import datetime
from collections import defaultdict

import matrix_benchmarking.store as store
import matrix_benchmarking.common as common
import matrix_benchmarking.cli_args as cli_args

EVT_TIME_FMT = "%Y-%m-%dT%H:%M:%S.%fZ"
TIME_FMT = "%Y-%m-%dT%H:%M:%SZ"

def parse_notebook_events(results, dirname):
    results.notebook_time = defaultdict(types.SimpleNamespace)
    results.notebook_start_time = datetime.datetime.now()

    with open(dirname / "notebook_events.yaml") as f:
        events = yaml.safe_load(f)

    for ev in events["items"]:
        if ev["involvedObject"]["kind"] != "Pod": continue
        if ev["involvedObject"]["namespace"] != "rhods-notebooks": continue

        podname = ev["involvedObject"]["name"]
        reason = ev.get("reason")
        time = ev.get("eventTime")
        fmt = EVT_TIME_FMT
        if not time:
            time = ev["lastTimestamp"]
            fmt = TIME_FMT

        eventTime = datetime.datetime.strptime(time, fmt)

        MAPPING_REASON_NAME = {
            "Scheduled": "creation_time",
            "AddedInterface": "pulling",
            "Pulled": "pulled",
            "Started": "started",
            "Killing": "terminated",
        }

        evt_name = MAPPING_REASON_NAME.get(reason)

        if evt_name and eventTime:
            results.notebook_start_time = min([results.notebook_start_time, eventTime])

            results.notebook_time[podname].__dict__[evt_name] = eventTime

def parse_execution_times(results, dirname):
    results.pod_time = {}

    with open(dirname / "tester_job.yaml") as f:
        job = yaml.safe_load(f)

    results.job_creation_time = \
        datetime.datetime.strptime(
            job["status"]["startTime"],
            TIME_FMT)
    results.job_completion_time = \
        datetime.datetime.strptime(
            job["status"]["completionTime"],
            TIME_FMT)

    with open(dirname / "tester_pods.yaml") as f:
        podlist = yaml.safe_load(f)

    for pod in podlist["items"]:
        podname = pod["metadata"]["name"]
        results.pod_time[podname] = types.SimpleNamespace()

        results.pod_time[podname].creation_time = \
            datetime.datetime.strptime(
                pod["metadata"]["creationTimestamp"],
                TIME_FMT)
        results.pod_time[podname].start_time = \
            datetime.datetime.strptime(
                pod["status"]["startTime"],
                TIME_FMT)

        if pod["status"]["containerStatuses"][0]["state"]["terminated"]:
            results.pod_time[podname].container_started = \
                datetime.datetime.strptime(
                    pod["status"]["containerStatuses"][0]["state"]["terminated"]["startedAt"],
                    TIME_FMT)

            results.pod_time[podname].container_finished = \
                datetime.datetime.strptime(
                    pod["status"]["containerStatuses"][0]["state"]["terminated"]["finishedAt"],
                    TIME_FMT)

        elif pod["status"]["containerStatuses"][0]["state"]["running"]:
            results.pod_time[podname].container_running_since = \
                datetime.datetime.strptime(
                    pod["status"]["containerStatuses"][0]["state"]["running"]["startedAt"],
                    TIME_FMT)

        else:
            import pdb;pdb.set_trace()

    pass

def parse_data():
    results_dir = pathlib.Path(".") / cli_args.kwargs["results_dirname"]

    settings = {"expe": "test", "value": "true"}
    results = types.SimpleNamespace()

    parse_execution_times(results, results_dir)
    parse_notebook_events(results, results_dir)

    store.add_to_matrix(settings, None, results, None)
