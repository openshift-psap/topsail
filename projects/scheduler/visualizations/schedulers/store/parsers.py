import types
import pathlib
import logging
import yaml
import os
import json
import datetime

import jsonpath_ng

import matrix_benchmarking.cli_args as cli_args
import matrix_benchmarking.store.prom_db as store_prom_db

import projects.matrix_benchmarking.visualizations.helpers.store as helpers_store
import projects.matrix_benchmarking.visualizations.helpers.store.parsers as helpers_store_parsers

from . import prom as workload_prom

register_important_file = None # will be when importing store/__init__.py

artifact_dirnames = types.SimpleNamespace()
artifact_dirnames.CLUSTER_DUMP_PROM_DB_DIR = "**/*__cluster__dump_prometheus_db"
artifact_dirnames.CLUSTER_CAPTURE_ENV_DIR = "*__cluster__capture_environment"
artifact_dirnames.SCHEDULER_GENERATE_LOAD_DIR = "*__scheduler__generate_load"
artifact_dirnames.SCHEDULER_CLEANUP = "*__scheduler__cleanup"
artifact_dirnames.RHODS_CAPTURE_STATE_DIR = "*__rhods__capture_state"

artifact_paths = types.SimpleNamespace() # will be dynamically populated


IMPORTANT_FILES = [
    "config.yaml",
    ".uuid",

    f"{artifact_dirnames.CLUSTER_DUMP_PROM_DB_DIR}/prometheus.t*",

    f"{artifact_dirnames.RHODS_CAPTURE_STATE_DIR}/nodes.json",
    f"{artifact_dirnames.RHODS_CAPTURE_STATE_DIR}/ocp_version.yml",
    f"{artifact_dirnames.RHODS_CAPTURE_STATE_DIR}/rhods.version",
    f"{artifact_dirnames.RHODS_CAPTURE_STATE_DIR}/rhods.createdAt",

    f"{artifact_dirnames.SCHEDULER_GENERATE_LOAD_DIR}/_ansible.play.yaml",
    f"{artifact_dirnames.SCHEDULER_GENERATE_LOAD_DIR}/pods.json",
    f"{artifact_dirnames.SCHEDULER_GENERATE_LOAD_DIR}/jobs.json",
    f"{artifact_dirnames.SCHEDULER_GENERATE_LOAD_DIR}/pytorchjob.json",
    f"{artifact_dirnames.SCHEDULER_GENERATE_LOAD_DIR}/appwrappers.json",
    f"{artifact_dirnames.SCHEDULER_GENERATE_LOAD_DIR}/workloads.json",

    f"{artifact_dirnames.SCHEDULER_GENERATE_LOAD_DIR}/start_end_cm.yaml",

    f"{artifact_dirnames.SCHEDULER_CLEANUP}/start_end_cm.yaml",
]

def ignore_file_not_found(fn):
    def decorator(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except FileNotFoundError as e:
            logging.warning(f"{fn.__name__}: FileNotFoundError: {e}")
            return None

    return decorator


def parse_always(results, dirname, import_settings):
    # parsed even when reloading from the cache file
    results.from_local_env = helpers_store_parsers.parse_local_env(dirname)


def parse_once(results, dirname):
    results.test_config = helpers_store_parsers.parse_test_config(dirname)
    results.test_case_config = _parse_test_case_config(dirname)
    results.test_case_properties = _parse_test_case_properties(results.test_case_config)

    results.target_kind = "AppWrapper" if results.test_case_properties.mode == "mcad" \
        else results.test_case_properties.resource_kind.title()

    if results.test_case_properties.mode == "mcad":
        results.target_kind_name = "AppWrapper"
    elif results.test_case_properties.mode == "job":
        results.target_kind_name = f"K8s {results.target_kind}"
    else:
        results.target_kind_name = f"{results.test_case_properties.mode.title()} {results.target_kind}"

    results.metrics = _extract_metrics(dirname)

    results.pod_times = _parse_pod_times(dirname)
    results.resource_times = _parse_resource_times(dirname, results.test_case_properties.mode, results.test_case_properties.resource_kind)
    results.test_start_end_time = _parse_test_start_end_time(dirname)
    if results.test_case_properties.mode == "mcad":
        results.cleanup_times = _parse_cleanup_start_end_time(dirname)
    else:
        results.cleanup_times = {}

    results.file_locations = _parse_file_locations(dirname)

    capture_state_dir = artifact_paths.RHODS_CAPTURE_STATE_DIR
    results.ocp_version = helpers_store_parsers.parse_ocp_version(dirname, capture_state_dir)
    results.rhods_info = helpers_store_parsers.parse_rhods_info(dirname, capture_state_dir, results.test_config.get("rhods.catalog.version_name"))
    results.from_env = helpers_store_parsers.parse_env(dirname, results.test_config, capture_state_dir)
    results.nodes_info = helpers_store_parsers.parse_nodes_info(dirname, capture_state_dir)
    results.cluster_info = helpers_store_parsers.extract_cluster_info(results.nodes_info)
    results.test_uuid = helpers_store_parsers.parse_test_uuid(dirname)


@ignore_file_not_found
def _extract_metrics(dirname):
    if not artifact_paths.CLUSTER_DUMP_PROM_DB_DIR:
        raise FileNotFoundError(artifact_dirnames.CLUSTER_DUMP_PROM_DB_DIR)

    db_files = {
        "sutest": (str(artifact_paths.CLUSTER_DUMP_PROM_DB_DIR / "prometheus.t*"), workload_prom.get_sutest_metrics()),
    }

    return helpers_store_parsers.extract_metrics(dirname, db_files)


@ignore_file_not_found
def _parse_pod_times(dirname):
    filename = artifact_paths.SCHEDULER_GENERATE_LOAD_DIR / "pods.json"

    with open(register_important_file(dirname, filename)) as f:
        try:
            json_file = json.load(f)
        except Exception as e:
            logging.error(f"Couldn't parse JSON file '{filename}': {e}")
            return

    pod_times = []
    for pod in json_file["items"]:
      pod_time = types.SimpleNamespace()
      pod_times.append(pod_time)

      pod_time.pod_name = pod["metadata"]["name"]

      pod_friendly_name = pod["metadata"]["labels"].get("job-name")
      if pod_friendly_name is None:
          pod_friendly_name = pod["metadata"]["labels"].get("training.kubeflow.org/job-name")

      pod_time.pod_friendly_name = pod_friendly_name
      pod_time.hostname = pod["spec"].get("nodeName")

      pod_time.creation_time = datetime.datetime.strptime(
              pod["metadata"]["creationTimestamp"], helpers_store_parsers.K8S_TIME_FMT)

      start_time_str = pod["status"].get("startTime")
      pod_time.start_time = None if not start_time_str else \
          datetime.datetime.strptime(start_time_str, helpers_store_parsers.K8S_TIME_FMT)
      pod_time.conditions = {}

      for condition in pod["status"].get("conditions", []):
          last_transition = datetime.datetime.strptime(condition["lastTransitionTime"], helpers_store_parsers.K8S_TIME_FMT)

          pod_time.conditions[condition["type"]] = last_transition

          if condition["type"] == "ContainersReady":
              pod_time.containers_ready = last_transition
          elif condition["type"] == "Initialized":
              pod_time.pod_initialized = last_transition
          elif condition["type"] == "PodScheduled":
              pod_time.pod_scheduled = last_transition

      for containerStatus in pod["status"].get("containerStatuses", []):
          try:
              finishedAt =  datetime.datetime.strptime(
                  containerStatus["state"]["terminated"]["finishedAt"],
                  helpers_store_parsers.K8S_TIME_FMT)
          except KeyError: continue

          # take the last container_finished found
          if ("container_finished" not in pod_time.__dict__
              or pod_time.container_finished < finishedAt):
              pod_time.container_finished = finishedAt

    return pod_times


def __parse_appwrapper_times(item, resource_times):
    if "annotations" in item["metadata"] and "scheduleTime" in item["metadata"]["annotations"]:
        resource_times.conditions["OC Created"] = datetime.datetime.strptime(
            item["metadata"]["annotations"]["scheduleTime"],
            helpers_store_parsers.K8S_TIME_FMT)

    elif not missing_label_warning_printed:
        missing_label_warning_printed = True
        logging.warning(f"scheduleTime label missing in AppWrapper {name} ...")

    resource_times.conditions["ETCD Created"] = resource_times.creation

    resource_times.completion = None
    if not item.get("status"): return

    if "controllerfirsttimestamp" in item["status"]:
        resource_times.conditions["Discovered"] = datetime.datetime.strptime(
            item["status"]["controllerfirsttimestamp"],
            helpers_store_parsers.K8S_TIME_MILLI_FMT)

    for condition in item["status"].get("conditions", []):
        if condition.get("reason") != "PodsCompleted": continue
        if condition.get("status") != "True": continue
        if condition.get("type") != "Completed": continue
        resource_times.completion = \
            datetime.datetime.strptime(
                condition["lastUpdateMicroTime"],
                helpers_store_parsers.K8S_TIME_MILLI_FMT)
        break

    for condition in item["status"]["conditions"]:
        resource_times.conditions[condition["type"]] = \
            datetime.datetime.strptime(
                condition["lastUpdateMicroTime"],
                helpers_store_parsers.K8S_TIME_MILLI_FMT)


def __parse_job_times(item, resource_times):
    resource_times.completion = \
        datetime.datetime.strptime(
            item["status"].get("completionTime"),
            helpers_store_parsers.K8S_TIME_FMT) \
            if item["status"].get("completionTime") else None


def __parse_workload_times(item, resource_times):
    resource_times.parent_job_name = item["metadata"]["ownerReferences"][0]["name"]

    resource_times.conditions["ETCD Created"] = resource_times.creation

    for condition in item["status"]["conditions"]:
        resource_times.conditions[condition["reason"]] = \
            datetime.datetime.strptime(
                condition["lastTransitionTime"],
                helpers_store_parsers.K8S_TIME_FMT)


def __parse_pytorchjob_times(item, resource_times):
    resource_times.conditions["ETCD Created"] = resource_times.creation

    resource_times.start = \
        datetime.datetime.strptime(
            item["status"].get("startTime"),
            helpers_store_parsers.K8S_TIME_FMT) \
            if item["status"].get("startTime") else None

    resource_times.completion = \
        datetime.datetime.strptime(
            item["status"].get("completionTime"),
            helpers_store_parsers.K8S_TIME_FMT) \
            if item["status"].get("completionTime") else None

    for condition in item["status"]["conditions"]:
        resource_times.conditions[condition["reason"]] = \
            datetime.datetime.strptime(
                condition["lastTransitionTime"],
                helpers_store_parsers.K8S_TIME_FMT)

    if resource_times.start and resource_times.completion:
        resource_times.duration = (resource_times.completion - resource_times.start).total_seconds()
    else:
        resource_times.duration = None


@ignore_file_not_found
def _parse_resource_times(dirname, mode, resource_type):
    all_resource_times = {}

    if not artifact_paths.SCHEDULER_GENERATE_LOAD_DIR:
        raise FileNotFoundError(artifact_dirnames.SCHEDULER_GENERATE_LOAD_DIR)

    @ignore_file_not_found
    def parse(fname):
        print(f"Parsing {fname} ...")
        file_path = artifact_paths.SCHEDULER_GENERATE_LOAD_DIR / fname

        with open(register_important_file(dirname, file_path)) as f:
            data = yaml.safe_load(f)

        missing_label_warning_printed = False
        for item in data["items"]:
            metadata = item["metadata"]

            kind = item["kind"]
            creationTimestamp = datetime.datetime.strptime(
                metadata["creationTimestamp"], helpers_store_parsers.K8S_TIME_FMT)

            name = metadata["name"]
            if kind == "Pod":
                generate_name, found, suffix = name.rpartition("-")
                remove_suffix = ((found and not suffix.isalpha()))

                if remove_suffix:
                    name = generate_name # remove generated suffix

            all_resource_times[f"{kind}/{name}"] = resource_times = types.SimpleNamespace()

            resource_times.kind = kind
            resource_times.name = name
            resource_times.creation = creationTimestamp
            resource_times.conditions = {}

            if kind == "AppWrapper":
                __parse_appwrapper_times(item, resource_times)

            elif kind == "Job":
                __parse_job_times(item, resource_times)
            elif kind == "Workload":
                __parse_workload_times(item, resource_times)
            elif kind == "PyTorchJob":
                __parse_pytorchjob_times(item, resource_times)
            else:
                logging.warning(f"Completion time parsing not supported for resource type {kind}.")


    parse(f"{resource_type}.json")

    if mode == "mcad":
        parse("appwrappers.json")
    if mode == "kueue":
        parse("workloads.json")
        for resource_time in all_resource_times.values():
            continue
            if resource_time.kind != "Workload": continue
            parent_job_time = all_resource_times[f"Job/{resource_time.parent_job_name}"]
            resource_time.conditions["Job Created"] = parent_job_time.creation

    return dict(all_resource_times)


@ignore_file_not_found
def _parse_test_start_end_time(dirname):
    with open(register_important_file(dirname, artifact_paths.SCHEDULER_GENERATE_LOAD_DIR / 'start_end_cm.yaml')) as f:
        start_end_cm = yaml.safe_load(f)

    test_start_end_time = types.SimpleNamespace()
    test_start_end_time.start = None
    test_start_end_time.end = None

    for cm in start_end_cm["items"]:
        name = cm["metadata"]["name"]
        ts = datetime.datetime.strptime(
            cm["metadata"]["creationTimestamp"],
            helpers_store_parsers.K8S_TIME_FMT)
        test_start_end_time.__dict__[name] = ts

    logging.debug(f'Start time: {test_start_end_time.start}')
    logging.debug(f'End time: {test_start_end_time.end}')

    return test_start_end_time


@ignore_file_not_found
def _parse_cleanup_start_end_time(dirname):
    with open(register_important_file(dirname, artifact_paths.SCHEDULER_CLEANUP / 'start_end_cm.yaml')) as f:
        configmaps = yaml.safe_load(f)

    cleanup_times = types.SimpleNamespace()
    cleanup_times.start = None
    cleanup_times.end = None

    for cm in configmaps["items"]:
        name = cm["metadata"]["name"]
        ts = datetime.datetime.strptime(
            cm["metadata"]["creationTimestamp"],
            helpers_store_parsers.K8S_TIME_FMT)
        cleanup_times.__dict__[name] = ts

    logging.debug(f'Start time: {cleanup_times.start}')
    logging.debug(f'End time: {cleanup_times.end}')

    return cleanup_times


@ignore_file_not_found
def _parse_test_case_config(dirname):
    test_case_config = {}
    with open(register_important_file(dirname, artifact_paths.SCHEDULER_GENERATE_LOAD_DIR / "_ansible.play.yaml")) as f:
        play = yaml.safe_load(f)
        play_vars = play[0]["vars"]
        for key, value in play_vars.items():
            _, found, name = key.partition("scheduler_generate_load_")
            if not found: continue
            test_case_config[name] = value

    return test_case_config


def _parse_test_case_properties(test_case_config):
    test_case_properties = types.SimpleNamespace()

    test_case_properties.count = test_case_config["count"]
    test_case_properties.pod_count = test_case_config["pod_count"]
    test_case_properties.pod_runtime = test_case_config["pod_runtime"]
    test_case_properties.total_pod_count = test_case_properties.count * test_case_properties.pod_count
    test_case_properties.mode = test_case_config["mode"]
    test_case_properties.resource_kind = test_case_config["resource_kind"]
    test_case_properties.launch_duration = test_case_config["timespan"]

    return test_case_properties


def _parse_file_locations(dirname):
    file_locations = types.SimpleNamespace()

    file_locations.test_config_file = pathlib.Path("config.yaml")
    register_important_file(dirname, file_locations.test_config_file)

    return file_locations
