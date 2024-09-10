import types
import pathlib
import logging
import yaml
import os
import json
import datetime
from collections import defaultdict
import dateutil.parser
import urllib.parse
import uuid

import matrix_benchmarking.cli_args as cli_args

import projects.matrix_benchmarking.visualizations.helpers.store as helpers_store
import projects.matrix_benchmarking.visualizations.helpers.store.parsers as helpers_store_parsers

from . import lts_parser

register_important_file = None # will be when importing store/__init__.py

artifact_dirnames = types.SimpleNamespace()
artifact_dirnames.LLM_LOAD_TEST_RUN_DIR = "*__llm_load_test__run"
artifact_dirnames.KSERVE_CAPTURE_STATE = "*__kserve__capture_state"
artifact_paths = types.SimpleNamespace() # will be dynamically populated

IMPORTANT_FILES = [
    "config.yaml",
    ".uuid",

    f"{artifact_dirnames.LLM_LOAD_TEST_RUN_DIR}/output/output.json",
    f"{artifact_dirnames.LLM_LOAD_TEST_RUN_DIR}/src/llm_load_test.config.yaml",
    f"{artifact_dirnames.KSERVE_CAPTURE_STATE}/_ansible.env",
    f"{artifact_dirnames.KSERVE_CAPTURE_STATE}/pods.json",
    f"{artifact_dirnames.KSERVE_CAPTURE_STATE}/ocp_version.yaml",
    f"{artifact_dirnames.KSERVE_CAPTURE_STATE}/rhods.createdAt",
    f"{artifact_dirnames.KSERVE_CAPTURE_STATE}/rhods.version",
    f"{artifact_dirnames.KSERVE_CAPTURE_STATE}/serving.json",
    f"{artifact_dirnames.KSERVE_CAPTURE_STATE}/nodes.json",
]


def parse_always(results, dirname, import_settings):
    # parsed even when reloading from the cache file

    results.from_local_env = helpers_store_parsers.parse_local_env(dirname)


def parse_once(results, dirname):
    results.test_config = helpers_store_parsers.parse_test_config(dirname)
    results.test_uuid = helpers_store_parsers.parse_test_uuid(dirname)

    results.llm_load_test_config = _parse_llm_load_test_config(dirname)
    results.llm_load_test_output = _parse_llm_load_test_output(dirname)
    results.predictor_logs = _parse_predictor_logs(dirname)
    results.predictor_pod = _parse_predictor_pod(dirname)
    results.inference_service = _parse_inference_service(dirname)
    results.test_start_end = _parse_test_start_end(dirname, results.llm_load_test_output)

    capture_state_dir = artifact_paths.KSERVE_CAPTURE_STATE
    results.ocp_version = helpers_store_parsers.parse_ocp_version(dirname, capture_state_dir)
    results.rhods_info = helpers_store_parsers.parse_rhods_info(dirname, capture_state_dir, results.test_config.get("rhods.catalog.version_name"))
    results.from_env = helpers_store_parsers.parse_env(dirname, results.test_config, capture_state_dir)
    results.nodes_info = helpers_store_parsers.parse_nodes_info(dirname, capture_state_dir)
    results.cluster_info = helpers_store_parsers.extract_cluster_info(results.nodes_info)


@helpers_store_parsers.ignore_file_not_found
def _parse_llm_load_test_output(dirname):
    llm_output_file = dirname / artifact_paths.LLM_LOAD_TEST_RUN_DIR / "output" / "output.json"
    register_important_file(dirname, llm_output_file.relative_to(dirname))

    with open(llm_output_file) as f:
        llm_load_test_output = json.load(f)

    return llm_load_test_output


@helpers_store_parsers.ignore_file_not_found
def _parse_llm_load_test_config(dirname):
    llm_config_file = dirname / artifact_paths.LLM_LOAD_TEST_RUN_DIR / "src" / "llm_load_test.config.yaml"
    register_important_file(dirname, llm_config_file.relative_to(dirname))

    llm_load_test_config = types.SimpleNamespace()

    with open(llm_config_file) as f:
        yaml_file = llm_load_test_config.yaml_file = yaml.safe_load(f)

    if not yaml_file:
        logging.error(f"Config file '{llm_config_file}' is empty ...")
        yaml_file = llm_load_test_config.yaml_file = {}

    llm_load_test_config.name = f"llm-load-test config {llm_config_file}"
    llm_load_test_config.get = helpers_store.get_yaml_get_key(llm_load_test_config.name, yaml_file)

    return llm_load_test_config


@helpers_store_parsers.ignore_file_not_found
def _parse_inference_service(dirname):
    if not artifact_paths.KSERVE_CAPTURE_STATE:
        logging.error(f"No '{artifact_dirnames.KSERVE_CAPTURE_STATE}' directory found in {dirname} ...")
        return

    capture_state_dir = artifact_paths.KSERVE_CAPTURE_STATE
    if isinstance(capture_state_dir, list):
        capture_state_dir = capture_state_dir[-1]

    inference_service = types.SimpleNamespace()
    serving_file = capture_state_dir / "serving.json"

    if (dirname / serving_file).exists():
        with open(register_important_file(dirname, serving_file)) as f:
            serving_def = json.load(f)

    if not serving_def["items"]:
        logging.error(f"No InferenceService found in {serving_file} ...")
        return inference_service

    inference_service_specs = [item for item in serving_def["items"] if item["kind"] == "InferenceService"]
    inference_service_specs = inference_service_specs[0]

    inference_service.min_replicas = helpers_store_parsers.dict_get_from_path(inference_service_specs, "spec.predictor.minReplicas", default=None)
    inference_service.max_replicas = helpers_store_parsers.dict_get_from_path(inference_service_specs, "spec.predictor.maxReplicas", default=None)

    return inference_service


@helpers_store_parsers.ignore_file_not_found
def _parse_predictor_pod(dirname):
    if not artifact_paths.KSERVE_CAPTURE_STATE:
        logging.error(f"No '{artifact_dirnames.KSERVE_CAPTURE_STATE}' directory found in {dirname} ...")
        return

    capture_state_dir = artifact_paths.KSERVE_CAPTURE_STATE
    if isinstance(capture_state_dir, list):
        capture_state_dir = capture_state_dir[-1]

    predictor_pod = types.SimpleNamespace()
    pods_def_file = capture_state_dir / "pods.json"

    if (dirname / pods_def_file).exists():
        with open(register_important_file(dirname, pods_def_file)) as f:
            pods_def = json.load(f)
    else:
        pods_def_file = pods_def_file.with_suffix(".yaml")
        with open(register_important_file(dirname, pods_def_file)) as f:
            logging.warning("Loading the predictor pod def as yaml ... (json file missing)")
            pods_def = yaml.safe_load(f)

    if not pods_def["items"]:
        logging.error(f"No container Pod found in {pods_def_file} ...")
        return predictor_pods

    pod = pods_def["items"][0]

    condition_times = {}
    for condition in pod["status"]["conditions"]:
        condition_times[condition["type"]] = \
            datetime.datetime.strptime(
                condition["lastTransitionTime"], helpers_store_parsers.K8S_TIME_FMT)

    containers_start_time = {}
    for container_status in pod["status"]["containerStatuses"]:
        try:
            containers_start_time[container_status["name"]] = \
                datetime.datetime.strptime(
                    container_status["state"]["running"]["startedAt"], helpers_store_parsers.K8S_TIME_FMT)
        except KeyError: pass # container not running


    predictor_pod.init_time = condition_times["Initialized"] - condition_times["PodScheduled"]
    predictor_pod.load_time = condition_times["Ready"] - condition_times["Initialized"]

    for container in pod["spec"]["containers"]:
        if container["name"] != "kserve-container": continue
        try:
            gpu_count = int(container["resources"]["requests"]["nvidia.com/gpu"])
        except:
            gpu_count = 0
        break
    else:
        logging.warning("Container 'kserve-container' not found in the predictor pod spec ...")
        gpu_count = None

    predictor_pod.gpu_count = gpu_count

    return predictor_pod


@helpers_store_parsers.ignore_file_not_found
def _parse_predictor_logs(dirname):
    if not artifact_paths.KSERVE_CAPTURE_STATE:
        logging.error(f"No '{artifact_dirnames.KSERVE_CAPTURE_STATE}' directory found in {dirname} ...")
        return

    kserve_capture_state_dir = artifact_paths.KSERVE_CAPTURE_STATE[-1] if isinstance(artifact_paths.KSERVE_CAPTURE_STATE, list) else artifact_paths.KSERVE_CAPTURE_STATE

    predictor_logs = types.SimpleNamespace()
    predictor_logs.distribution = defaultdict(int)
    predictor_logs.line_count = 0

    for log_file in (dirname / kserve_capture_state_dir).glob("logs/*.log"):

        for line in open(log_file).readlines():
            predictor_logs.line_count += 1

            if '"severity":"ERROR"' in line:
                predictor_logs.distribution["errors"] += 1
            if '"channel": "DESTROY-THRD"' in line:
                predictor_logs.distribution["DESTROY-THRD"] += 1
            if '"channel": "ABORT-ACTION"' in line:
                predictor_logs.distribution["ABORT-ACTION"] += 1

    return predictor_logs


def _parse_test_start_end(dirname, llm_load_test_output):
    if not llm_load_test_output:
        return None

    test_start_end = types.SimpleNamespace()
    test_start_end.start = None
    test_start_end.end = None

    for result in llm_load_test_output.get("results") or []:
        start = datetime.datetime.fromtimestamp(result["start_time"])
        end = datetime.datetime.fromtimestamp(result["end_time"])

        if test_start_end.start is None or start < test_start_end.start:
            test_start_end.start = start

        if test_start_end.end is None or end > test_start_end.end:
            test_start_end.end = end

    if test_start_end.start is None:
        logging.warning("Could not find the start time of the test...")
    if test_start_end.end is None:
        logging.warning("Could not find the end time of the test...")

    return test_start_end
