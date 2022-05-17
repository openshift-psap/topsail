import types
import pathlib
import yaml
import datetime
from collections import defaultdict

import matrix_benchmarking.store as store
import matrix_benchmarking.store.simple as store_simple
import matrix_benchmarking.common as common
import matrix_benchmarking.cli_args as cli_args

EVT_TIME_FMT = "%Y-%m-%dT%H:%M:%S.%fZ"
TIME_FMT = "%Y-%m-%dT%H:%M:%SZ"

def _rewrite_settings(settings_dict):
    return settings_dict

def _parse_job(results, filename):

    with open(filename) as f:
        job = yaml.safe_load(f)

    results.job_creation_time = \
        datetime.datetime.strptime(
            job["status"]["startTime"],
            TIME_FMT)
    results.job_completion_time = \
        datetime.datetime.strptime(
            job["status"]["completionTime"],
            TIME_FMT)


def _parse_pod_event_times(filename, namespace=None, hostnames=None):
    event_times = defaultdict(types.SimpleNamespace)

    with open(filename) as f:
        events = yaml.safe_load(f)

    for ev in events["items"]:
        if namespace and ev["involvedObject"]["namespace"] != namespace: continue

        if ev["involvedObject"]["kind"] == "PersistentVolumeClaim":
            podname = ev["involvedObject"]["name"].strip("-pvc")
            appears_time = event_times[podname].__dict__.get("appears_time")
            str_time = ev["firstTimestamp"]
            event_time = datetime.datetime.strptime(str_time,  TIME_FMT)

            if not appears_time or event_time < appears_time:
                event_times[podname].appears_time = event_time

        elif ev["involvedObject"]["kind"] != "Pod":
            continue

        podname = ev["involvedObject"]["name"]

        if podname.endswith("-build"): continue
        if podname.endswith("-debug"): continue

        reason = ev.get("reason")
        time = ev.get("eventTime")
        fmt = EVT_TIME_FMT
        if not time:
            time = ev["lastTimestamp"]
            fmt = TIME_FMT

        event_time = datetime.datetime.strptime(time, fmt)

        MAPPING_REASON_NAME = {
            "Scheduled": "scheduled",
            "AddedInterface": "pulling",
            "Pulled": "pulled",
            "Started": "started",
            "Killing": "terminated",
            "FailedScheduling": "failedScheduling",
        }

        evt_name = MAPPING_REASON_NAME.get(reason)

        if not (evt_name and event_time):
            continue


        if evt_name == "failedScheduling":
            start = datetime.datetime.strptime(ev["firstTimestamp"], fmt)
            event_times[podname].failedScheduling = [start, event_time, ev["message"]]
            continue


        event_times[podname].__dict__[evt_name] = event_time

        if hostnames is not None and reason == "Started":
            hostnames[podname] = ev["source"]["host"]

    return event_times


def _parse_pod_times(filename):
    pod_times = defaultdict(types.SimpleNamespace)
    with open(filename) as f:
        podlist = yaml.safe_load(f)

    for pod in podlist["items"]:
        podname = pod["metadata"]["name"]

        if podname.endswith("-build"): continue
        if podname.endswith("-debug"): continue

        pod_times[podname] = types.SimpleNamespace()

        pod_times[podname].creation_time = \
            datetime.datetime.strptime(
                pod["metadata"]["creationTimestamp"],
                TIME_FMT)
        pod_times[podname].start_time = \
            datetime.datetime.strptime(
                pod["status"]["startTime"],
                TIME_FMT)

        if pod["status"]["containerStatuses"][0]["state"]["terminated"]:
            pod_times[podname].container_started = \
                datetime.datetime.strptime(
                    pod["status"]["containerStatuses"][0]["state"]["terminated"]["startedAt"],
                    TIME_FMT)

            pod_times[podname].container_finished = \
                datetime.datetime.strptime(
                    pod["status"]["containerStatuses"][0]["state"]["terminated"]["finishedAt"],
                    TIME_FMT)

        elif pod["status"]["containerStatuses"][0]["state"]["running"]:
            pod_times[podname].container_running_since = \
                datetime.datetime.strptime(
                    pod["status"]["containerStatuses"][0]["state"]["running"]["startedAt"],
                    TIME_FMT)

        else:
            print("Unknown containerStatuses ...")
            import pdb;pdb.set_trace()
            pass

    return pod_times

def _parse_directory(fn_add_to_matrix, dirname, import_settings):
    results = types.SimpleNamespace()

    _parse_job(results, dirname / "tester_job.yaml")

    results.pod_times = _parse_pod_times(dirname / "tester_pods.yaml")
    results.event_times = defaultdict(types.SimpleNamespace)
    results.notebook_hostnames = notebook_hostnames = {}
    results.testpod_hostnames = testpod_hostnames = {}

    results.event_times |= _parse_pod_event_times(dirname / "notebook_events.yaml", "rhods-notebooks", notebook_hostnames)
    results.event_times |= _parse_pod_event_times(dirname / "tester_events.yaml", "loadtest", testpod_hostnames)

    results.test_pods = [k for k in results.event_times.keys() if k.startswith("ods-ci")]
    results.notebook_pods = [k for k in results.event_times.keys() if k.startswith("jupyterhub-nb")]

    store.add_to_matrix(import_settings, None, results, None)

def parse_data():
    # delegate the parsing to the simple_store
    store.register_custom_rewrite_settings(_rewrite_settings)
    store_simple.register_custom_parse_results(_parse_directory)

    return store_simple.parse_data()
