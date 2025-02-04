import types
import pathlib
import logging
import yaml
import os
import json
import datetime
import dateutil

import matrix_benchmarking.cli_args as cli_args
import matrix_benchmarking.store.prom_db as store_prom_db

import projects.matrix_benchmarking.visualizations.helpers.store.parsers as helpers_store_parsers

from . import prom as workload_prom

register_important_file = None # will be when importing store/__init__.py

K8S_TIME_FMT = "%Y-%m-%dT%H:%M:%SZ"
SHELL_DATE_TIME_FMT = "%a %b %d %H:%M:%S %Z %Y"
ANSIBLE_LOG_DATE_TIME_FMT = "%Y-%m-%d %H:%M:%S"

artifact_dirnames = types.SimpleNamespace()
artifact_dirnames.CLUSTER_CAPTURE_ENV_DIR = "*__cluster__capture_environment"
artifact_dirnames.LOCAL_CI_RUN_MULTI_DIR = "*__local_ci__run_multi"
artifact_dirnames.KSERVE_CAPTURE_OPERATORS_STATE_DIR = "*__kserve__capture_operators_state"

artifact_paths = types.SimpleNamespace() # store._parse_directory will turn it into a {str: pathlib.Path} dict base on ^^^

IMPORTANT_FILES = [
    "config.yaml",
    ".uuid",

    f"{artifact_dirnames.LOCAL_CI_RUN_MULTI_DIR}/ci_job.yaml",
    f"{artifact_dirnames.LOCAL_CI_RUN_MULTI_DIR}/prometheus_ocp.t*",
    f"{artifact_dirnames.LOCAL_CI_RUN_MULTI_DIR}/success_count",
    f"{artifact_dirnames.LOCAL_CI_RUN_MULTI_DIR}/artifacts/ci-pod-*/progress_ts.yaml",
    f"{artifact_dirnames.LOCAL_CI_RUN_MULTI_DIR}/artifacts/ci-pod-*/test.exit_code",
    f"{artifact_dirnames.LOCAL_CI_RUN_MULTI_DIR}/artifacts/ci-pod-*/test.exit_code",
    f"{artifact_dirnames.LOCAL_CI_RUN_MULTI_DIR}/artifacts/ci-pod-*/*__kserve__capture_state/serving.json",
    f"{artifact_dirnames.LOCAL_CI_RUN_MULTI_DIR}/artifacts/ci-pod-*/*__kserve__validate_model_caikit-isvc-u*-m*/caikit-isvc-u*-m*/call_*.json",
    f"{artifact_dirnames.CLUSTER_CAPTURE_ENV_DIR}/nodes.json",
    f"{artifact_dirnames.CLUSTER_CAPTURE_ENV_DIR}/ocp_version.yml",
    f"{artifact_dirnames.KSERVE_CAPTURE_OPERATORS_STATE_DIR}/rhods.createdAt",
    f"{artifact_dirnames.KSERVE_CAPTURE_OPERATORS_STATE_DIR}/rhods.version",
    f"{artifact_dirnames.KSERVE_CAPTURE_OPERATORS_STATE_DIR}/predictor_pods.json",
]


def parse_always(results, dirname, import_settings):
    # parsed even when reloading from the cache file
    results.from_local_env = helpers_store_parsers.parse_local_env(dirname)


def parse_once(results, dirname):
    results.test_config = helpers_store_parsers.parse_test_config(dirname)

    results.user_count = int(results.test_config.get("tests.scale.namespace.replicas"))
    results.test_uuid = helpers_store_parsers.parse_test_uuid(dirname)

    results.metrics = _extract_metrics(dirname)
    results.test_start_end_time = _parse_start_end_time(dirname)
    results.user_data = _parse_user_data(dirname, results.user_count)
    results.success_count = _parse_success_count(dirname)
    results.file_locations = _parse_file_locations(dirname)
    results.pod_times = _parse_pod_times(dirname)

    capture_state_dir = artifact_paths.KSERVE_CAPTURE_OPERATORS_STATE_DIR
    results.ocp_version = helpers_store_parsers.parse_ocp_version(dirname, capture_state_dir)
    results.rhods_info = helpers_store_parsers.parse_rhods_info(dirname, capture_state_dir, results.test_config.get("rhods.catalog.version_name"))
    results.from_env = helpers_store_parsers.parse_env(dirname, results.test_config, capture_state_dir)
    results.nodes_info = helpers_store_parsers.parse_nodes_info(dirname, capture_state_dir)
    results.cluster_info = helpers_store_parsers.extract_cluster_info(results.nodes_info)

def _extract_metrics(dirname):
    db_files = {
        "sutest": (str(artifact_paths.LOCAL_CI_RUN_MULTI_DIR / "prometheus_ocp.t*"), workload_prom.get_sutest_metrics()),
    }

    return helpers_store_parsers.extract_metrics(dirname, db_files)

@helpers_store_parsers.ignore_file_not_found
def _parse_start_end_time(dirname):
    test_start_end_time = types.SimpleNamespace()
    test_start_end_time.start = None
    test_start_end_time.end = None

    with open(register_important_file(dirname, artifact_paths.LOCAL_CI_RUN_MULTI_DIR / "ci_job.yaml")) as f:
        job = yaml.safe_load(f)

    test_start_end_time.start = \
        datetime.datetime.strptime(
            job["status"]["startTime"],
            K8S_TIME_FMT)

    if job["status"].get("completionTime"):
        test_start_end_time.end = \
            datetime.datetime.strptime(
                job["status"]["completionTime"],
                K8S_TIME_FMT)
    else:
        test_start_end_time.end = test_start_end_time.start + datetime.timedelta(hours=1)

    return test_start_end_time


@helpers_store_parsers.ignore_file_not_found
def _parse_success_count(dirname):
    filename = pathlib.Path("000__local_ci__run_multi") / "success_count"

    with open(register_important_file(dirname, filename)) as f:
        content = f.readline()

    success_count = int(content.split("/")[0])

    return success_count


@helpers_store_parsers.ignore_file_not_found
def _parse_user_exit_code(dirname, ci_pod_dir):
    filename = (ci_pod_dir / "test.exit_code").relative_to(dirname)
    with open(register_important_file(dirname, filename)) as f:
        exit_code = int(f.readline())

    return exit_code


@helpers_store_parsers.ignore_file_not_found
def _parse_user_progress(dirname, ci_pod_dir):
    filename = (ci_pod_dir / "progress_ts.yaml").relative_to(dirname)
    with open(register_important_file(dirname, filename)) as f:
        progress_src = yaml.safe_load(f)

    progress = {}
    for idx, (key, date_str) in enumerate(progress_src.items()):
        progress[f"progress_ts.{idx:03d}__{key}"] = datetime.datetime.strptime(date_str, SHELL_DATE_TIME_FMT)

    return progress


def _parse_user_data(dirname, user_count):
    user_data = {}
    for user_id in range(user_count):
        ci_pod_dirname = artifact_paths.LOCAL_CI_RUN_MULTI_DIR / "artifacts" / f"ci-pod-{user_id}"
        ci_pod_dirpath = dirname / ci_pod_dirname
        if not (dirname / ci_pod_dirname).exists():
            user_data[user_id] = None
            logging.warning(f"No user directory collected for user #{user_id} ({ci_pod_dirname})")
            continue

        user_data[user_id] = data = types.SimpleNamespace()
        data.artifact_dir = ci_pod_dirname
        data.exit_code = _parse_user_exit_code(dirname, ci_pod_dirpath)
        data.progress = _parse_user_progress(dirname, ci_pod_dirpath)
        data.resource_times = _parse_user_resource_times(dirname, ci_pod_dirpath)
        data.grpc_calls = _parse_user_grpc_calls(dirname, ci_pod_dirpath)

    return user_data


def _parse_file_locations(dirname):
    file_locations = types.SimpleNamespace()

    file_locations.test_config_file = pathlib.Path("config.yaml")
    register_important_file(dirname, file_locations.test_config_file)

    return file_locations


@helpers_store_parsers.ignore_file_not_found
def _parse_pod_times(dirname):
    filename = artifact_paths.KSERVE_CAPTURE_OPERATORS_STATE_DIR / "predictor_pods.json"

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

      pod_time.namespace = pod["metadata"]["namespace"]
      pod_time.pod_name = pod["metadata"]["name"]

      pod_time.hostname = pod["spec"].get("nodeName")

      pod_time.creation_time = datetime.datetime.strptime(
              pod["metadata"]["creationTimestamp"], K8S_TIME_FMT)

      pod_time.user_idx = int(pod_time.namespace.split("-u")[-1])
      pod_time.model_id = int(pod["metadata"]["name"].split("-m")[1].split("-")[0])
      pod_time.pod_friendly_name = f"model_{pod_time.model_id}"

      start_time_str = pod["status"].get("startTime")
      pod_time.start_time = None if not start_time_str else \
          datetime.datetime.strptime(start_time_str, K8S_TIME_FMT)

      for condition in pod["status"].get("conditions", []):
          last_transition = datetime.datetime.strptime(condition["lastTransitionTime"], K8S_TIME_FMT)

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
                  K8S_TIME_FMT)
          except KeyError: continue

          # take the last container_finished found
          if ("container_finished" not in pod_time.__dict__
              or pod_time.container_finished < finishedAt):
              pod_time.container_finished = finishedAt

    return pod_times


@helpers_store_parsers.ignore_file_not_found
def _parse_user_resource_times(dirname, ci_pod_dir):
    resource_times = {}

    glob_expansion = list(ci_pod_dir.glob("*__kserve__capture_state"))
    if not glob_expansion:
        raise FileNotFoundError(f"'*__kserve__capture_state' not found in {ci_pod_dir}")

    _file_path = glob_expansion[0] / "serving.json"
    file_path = _file_path.relative_to(dirname)

    with open(register_important_file(dirname, file_path)) as f:
        data = json.load(f)

    for item in data["items"]:
        metadata = item["metadata"]

        kind = item["kind"]
        creationTimestamp = datetime.datetime.strptime(
            metadata["creationTimestamp"], K8S_TIME_FMT)

        name = metadata["name"]
        namespace = metadata["namespace"]
        generate_name, found, suffix = name.rpartition("-")
        remove_suffix = ((found and not suffix.isalpha()))

        def isvc_name_to_model_id(isvc_name):
            return int(isvc_name.split("-m")[1].split("-")[0])

        def isvc_name_to_friendly_name(isvc_name):
            model_id = isvc_name_to_model_id(isvc_name)

            return f"model_{model_id}"

        if kind == "InferenceService":
            model_id = isvc_name_to_model_id(name)
            name = isvc_name_to_friendly_name(name)
            remove_suffix = False

        if kind in ("Revision", "Configuration", "Service", "Route"):
            isvc_name = metadata["labels"]["serving.kserve.io/inferenceservice"]
            name = isvc_name_to_friendly_name(isvc_name)
            remove_suffix = False
            model_id = isvc_name_to_model_id(isvc_name)

        if kind == "ServingRuntime":
            model_id = -1

        if remove_suffix:
            name = generate_name # remove generated suffix

        resource_times[f"{kind}/{name}"] = obj_resource_times = types.SimpleNamespace()
        user_idx = int(namespace.split("-u")[-1])

        obj_resource_times.kind = kind
        obj_resource_times.name = name
        obj_resource_times.namespace = namespace
        obj_resource_times.creation = creationTimestamp
        obj_resource_times.model_id = model_id
        obj_resource_times.user_idx = user_idx

        if kind in ("InferenceService", "Revision"):
            obj_resource_times.conditions = {}
            for condition in item["status"].get("conditions", []):
                if not condition["status"]: continue

                ts = datetime.datetime.strptime(condition["lastTransitionTime"], K8S_TIME_FMT)
                obj_resource_times.conditions[condition["type"]] = ts

    return dict(resource_times)


@helpers_store_parsers.ignore_file_not_found
def _parse_user_grpc_calls(dirname, ci_pod_dir):
    grpc_calls = []

    files_path = (dirname / ci_pod_dir).glob("*__kserve__validate_model_caikit-isvc-u*-m*/caikit-isvc-u*-m*/call_*.json")

    today = datetime.datetime.today()
    today_min = datetime.datetime.combine(today, datetime.time.min)

    for _file_path in files_path:
        file_path = _file_path.relative_to(dirname)

        with open(register_important_file(dirname, file_path)) as f:
            data = json.load(f)

            grpc_call = types.SimpleNamespace()
            grpc_call.name = file_path.stem.replace("call_", "")
            delta = datetime.datetime.combine(today, dateutil.parser.parse(data["delta"]).time()) - today_min
            grpc_call.duration = delta

            grpc_call.attempts = data["attempts"]
            grpc_call.isvc = file_path.parent.name
            grpc_calls.append(grpc_call)

    return grpc_calls
