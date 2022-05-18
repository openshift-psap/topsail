import types
import pathlib
import yaml
import datetime
from collections import defaultdict
import xmltodict
import logging

import matrix_benchmarking.store as store
import matrix_benchmarking.store.simple as store_simple
import matrix_benchmarking.common as common
import matrix_benchmarking.cli_args as cli_args
import matrix_benchmarking.store.prom_db as store_prom_db

K8S_EVT_TIME_FMT = "%Y-%m-%dT%H:%M:%S.%fZ"
K8S_TIME_FMT = "%Y-%m-%dT%H:%M:%SZ"
ROBOT_TIME_FMT = "%Y%m%d %H:%M:%S.%f"

def _rewrite_settings(settings_dict):
    return settings_dict


SUTEST_METRICS = [
    "pod:container_cpu_usage:sum",
    "rate(container_cpu_usage_seconds_total[60y])",
]

DRIVER_METRICS = [
    "pod:container_cpu_usage:sum",
    "rate(container_cpu_usage_seconds_total[60y])",
]

RHODS_METRICS = [
]

def _parse_job(results, filename):

    with open(filename) as f:
        job = yaml.safe_load(f)

    results.job_creation_time = \
        datetime.datetime.strptime(
            job["status"]["startTime"],
            K8S_TIME_FMT)
    results.job_completion_time = \
        datetime.datetime.strptime(
            job["status"]["completionTime"],
            K8S_TIME_FMT)


def _parse_pod_event_times(filename, namespace=None, hostnames=None):
    event_times = defaultdict(types.SimpleNamespace)

    with open(filename) as f:
        events = yaml.safe_load(f)

    for ev in events["items"]:
        if namespace and ev["involvedObject"]["namespace"] != namespace: continue

        if ev["involvedObject"]["kind"] != "Pod":
            continue

        podname = ev["involvedObject"]["name"]

        if podname.endswith("-build"): continue
        if podname.endswith("-debug"): continue

        reason = ev.get("reason")
        time = ev.get("eventTime")
        fmt = K8S_EVT_TIME_FMT
        if not time:
            time = ev["lastTimestamp"]
            fmt = K8S_TIME_FMT

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
            if "count" in ev:
                start = datetime.datetime.strptime(ev["firstTimestamp"], fmt)
                end = event_time
            else:
                start = event_time
                end = event_time + datetime.timedelta(minutes=1)

            event_times[podname].failedScheduling = [start, end, ev["message"]]
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
                K8S_TIME_FMT)
        pod_times[podname].start_time = \
            datetime.datetime.strptime(
                pod["status"]["startTime"],
                K8S_TIME_FMT)

        if pod["status"]["containerStatuses"][0]["state"]["terminated"]:
            pod_times[podname].container_started = \
                datetime.datetime.strptime(
                    pod["status"]["containerStatuses"][0]["state"]["terminated"]["startedAt"],
                    K8S_TIME_FMT)

            pod_times[podname].container_finished = \
                datetime.datetime.strptime(
                    pod["status"]["containerStatuses"][0]["state"]["terminated"]["finishedAt"],
                    K8S_TIME_FMT)

        elif pod["status"]["containerStatuses"][0]["state"]["running"]:
            pod_times[podname].container_running_since = \
                datetime.datetime.strptime(
                    pod["status"]["containerStatuses"][0]["state"]["running"]["startedAt"],
                    K8S_TIME_FMT)

        else:
            print("Unknown containerStatuses ...")
            import pdb;pdb.set_trace()
            pass

    return pod_times


def _parse_ods_ci_output_xml(filename):
    ods_ci_times = {}

    with open(filename) as f:
        output_dict = xmltodict.parse(f.read())

    for test in output_dict["robot"]["suite"]["test"]:
        ods_ci_times[test["@name"]] = test_times = types.SimpleNamespace()

        test_times.start = datetime.datetime.strptime(test["status"]["@starttime"], ROBOT_TIME_FMT)
        test_times.finish = datetime.datetime.strptime(test["status"]["@endtime"], ROBOT_TIME_FMT)
        test_times.status = test["status"]["@status"]

    return ods_ci_times


def _extract_metrics(dirname):
    METRICS = {
        "sutest": ("sutest_prometheus.tgz", SUTEST_METRICS),
        "driver": ("driver_prometheus.tgz", DRIVER_METRICS),
        "rhods":  ("rhods_prometheus.tgz", RHODS_METRICS),
    }

    results_metrics = {}
    for name, (filename_tgz, metrics) in METRICS.items():
        try:
            results_metrics[name] = store_prom_db.extract_metrics(dirname / filename_tgz, metrics, dirname,
                                                                  filename_prefix=f"{name}_")
        except FileNotFoundError:
            logging.warning(f"No {filename_tgz} in '{dirname}'.")

    return results_metrics


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

    results.metrics = _extract_metrics(dirname)

    results.ods_ci_output = {}
    for test_pod in results.test_pods:
        ods_ci_dirname = test_pod.rpartition("-")[0]
        output_file = dirname / "ods-ci" / ods_ci_dirname / "output.xml"
        if not output_file.is_file(): continue
        results.ods_ci_output[test_pod] = _parse_ods_ci_output_xml(output_file)

    store.add_to_matrix(import_settings, None, results, None)

def parse_data():
    # delegate the parsing to the simple_store
    store.register_custom_rewrite_settings(_rewrite_settings)
    store_simple.register_custom_parse_results(_parse_directory)

    return store_simple.parse_data()
