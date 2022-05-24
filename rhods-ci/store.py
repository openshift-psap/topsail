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
            "FailedScheduling": "failed",
            "Failed": "failed"
        }

        evt_name = MAPPING_REASON_NAME.get(reason)

        if not (evt_name and event_time):
            continue

        if evt_name == "failed":
            if "count" in ev:
                start = datetime.datetime.strptime(ev["firstTimestamp"], fmt)
                end = event_time
                if start == end:
                    end += datetime.timedelta(seconds=10)
            else:
                start = event_time
                end = event_time + datetime.timedelta(seconds=10)

            if "warnings" not in event_times[podname].__dict__:
                event_times[podname].__dict__["warnings"] = []

            event_times[podname].__dict__["warnings"].append([reason, start, end, ev["message"]])
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

    tests = output_dict["robot"]["suite"]["test"]
    if not isinstance(tests, list): tests = [tests]

    for test in tests:
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


def _generate_pod_event_times(user_count, instance_count, container_size, instance_cpu, instance_memory):
    event_times = defaultdict(types.SimpleNamespace)
    notebook_hostnames = {}

    NOTEBOOK_REQUESTS = dict(
        default=types.SimpleNamespace(cpu=1, memory=4),
        small=types.SimpleNamespace(cpu=1,   memory=8),
        medium=types.SimpleNamespace(cpu=3,  memory=24),
    )

    POD_CREATION = 5
    PULL_TIME_COLD = 120
    PULL_TIME_HOT = 10
    POD_INITIALIZATION = 15
    NOTEBOOK_EXECUTION_TIME = 5*60

    def find_node():
        for node in nodes:
            if node.cpu < notebook_rq.cpu or node.memory < notebook_rq.memory:
                continue
            node.cpu -= notebook_rq.cpu
            node.memory -= notebook_rq.memory

            return node
        return None

    def reset_nodes():
        for node in nodes:
            node.cpu = instance_cpu
            node.memory = instance_memory

    def add_time(evt, previous, current, timespan_seconds):
        prev = evt.__dict__[previous]
        evt.__dict__[current] = prev + datetime.timedelta(seconds=timespan_seconds)

    users = list(range(user_count))
    nodes = [types.SimpleNamespace(idx=instance_idx, cpu=instance_cpu, memory=instance_memory)
             for instance_idx in range(instance_count)]

    notebook_rq = NOTEBOOK_REQUESTS[container_size]
    print(f"{user_count} users using {instance_count} x {{ {instance_cpu} CPUS ; {instance_memory} GB of RAM }} instances, requesting {notebook_rq.cpu} CPUs & {notebook_rq.memory} GB of RAM per notebook")
    current_time = datetime.datetime.now()

    execution_round = 0
    while users:
        users_scheduled = []
        current_end = None
        for user_idx in users:
            podname = f"jupyterhub-nb-testuser{user_idx}"
            if "warnings" not in event_times[podname].__dict__:
                event_times[podname].warnings = []

            node = find_node()

            if not node:
                if not event_times[podname].warnings:
                    event_times[podname].warnings.append(["FailedScheduling",
                                                          current_time, None,
                                                          "no node available"])
                continue

            if event_times[podname].warnings:
                event_times[podname].warnings[-1][2] = current_time

            notebook_hostnames[f"jupyterhub-nb-testuser{user_idx}"] = f"Node {node.idx}"

            event_times[podname].scheduled = current_time
            add_time(event_times[podname], "scheduled", "pulling", POD_CREATION)
            add_time(event_times[podname], "pulling", "pulled", PULL_TIME_COLD if execution_round == 0 else PULL_TIME_HOT)
            add_time(event_times[podname], "pulled", "started", POD_INITIALIZATION)
            add_time(event_times[podname], "started", "terminated", NOTEBOOK_EXECUTION_TIME)

            users_scheduled.append(user_idx)
            current_end = event_times[podname].terminated

        for user_idx in users_scheduled:
            users.remove(user_idx)

        execution_round += 1
        current_time = current_end
        reset_nodes()

    return event_times, notebook_hostnames


def _generate_timeline_results(entry, user_count):
    results = types.SimpleNamespace()

    results.testpod_hostnames = {f"ods-ci-{idx}": "Node 0" for idx in range(user_count)}

    results.notebook_hostnames = {f"jupyterhub-nb-testuser{idx}": f"Node {idx}" for idx in range(user_count)}

    results.pod_times = {}
    results.test_pods = []

    results.ods_ci_output = {}

    results.test_pods = []
    results.job_creation_time = datetime.datetime.now()
    results.job_completion_time = datetime.datetime.now() + datetime.timedelta(minutes=5)

    results.event_times, results.notebook_hostnames = \
        _generate_pod_event_times(user_count,
                                  entry.import_settings["instance_count"],
                                  "default",
                                  entry.results.vcpu, entry.results.ram)

    results.notebook_pods = list(results.event_times.keys())

    return results


def _populate_theoretical_data():
    with open("data/machines") as f:
        for _line in f.readlines():
            line = _line.strip()
            if not line or line.startswith("#"): continue

            instance, vcpu, ram, price, *accel = line.split(", ")

            results = types.SimpleNamespace()
            results.vcpu = int(vcpu.split()[0])
            results.ram = int(ram.split()[0])
            results.price = float(price[1:])

            import_settings = {
                "expe": "theoretical",
                "instance": instance,
                "instance_count": 2,
            }

            store.add_to_matrix(import_settings, None, results, None)


def parse_data():
    # delegate the parsing to the simple_store
    store.register_custom_rewrite_settings(_rewrite_settings)
    store_simple.register_custom_parse_results(_parse_directory)

    _populate_theoretical_data()

    return store_simple.parse_data()
