import types
import pathlib
import logging
import yaml
import os
import json
import datetime
import urllib
import uuid

import jsonpath_ng

import matrix_benchmarking.cli_args as cli_args

import projects.matrix_benchmarking.visualizations.helpers.store as helpers_store
import projects.matrix_benchmarking.visualizations.helpers.store.parsers as helpers_store_parsers

register_important_file = None # will be when importing store/__init__.py

K8S_TIME_FMT = "%Y-%m-%dT%H:%M:%SZ"
SHELL_DATE_TIME_FMT = "%a %b %d %H:%M:%S %Z %Y"
ANSIBLE_LOG_DATE_TIME_FMT = "%Y-%m-%d %H:%M:%S"

artifact_dirnames = types.SimpleNamespace()
artifact_dirnames.CLUSTER_CAPTURE_ENV_DIR = "*__cluster__capture_environment"
artifact_dirnames.FINE_TUNING_RUN_FINE_TUNING_DIR = "*__fine_tuning__run_fine_tuning_job"
artifact_dirnames.RHODS_CAPTURE_STATE = "*__rhods__capture_state"
artifact_paths = types.SimpleNamespace() # will be dynamically populated

IMPORTANT_FILES = [
    ".uuid",
    "config.yaml",
    f"{artifact_dirnames.CLUSTER_CAPTURE_ENV_DIR}/_ansible.log",
    f"{artifact_dirnames.CLUSTER_CAPTURE_ENV_DIR}/nodes.json",
    f"{artifact_dirnames.CLUSTER_CAPTURE_ENV_DIR}/ocp_version.yml",
    f"{artifact_dirnames.FINE_TUNING_RUN_FINE_TUNING_DIR}/src/config_final.json",
    f"{artifact_dirnames.FINE_TUNING_RUN_FINE_TUNING_DIR}/artifacts/pod.log",
    f"{artifact_dirnames.FINE_TUNING_RUN_FINE_TUNING_DIR}/artifacts/pod.json",
    f"{artifact_dirnames.FINE_TUNING_RUN_FINE_TUNING_DIR}/_ansible.play.yaml",
    f"{artifact_dirnames.RHODS_CAPTURE_STATE}/rhods.createdAt",
    f"{artifact_dirnames.RHODS_CAPTURE_STATE}/rhods.version",
]


def parse_always(results, dirname, import_settings):
    # parsed even when reloading from the cache file
    results.from_local_env = helpers_store_parsers.parse_local_env(dirname)

    pass


def parse_once(results, dirname):
    results.test_config = helpers_store_parsers.parse_test_config(dirname)
    results.test_uuid = helpers_store_parsers.parse_test_uuid(dirname)

    capture_state_dir = artifact_paths.CLUSTER_CAPTURE_ENV_DIR
    results.ocp_version = helpers_store_parsers.parse_ocp_version(dirname, capture_state_dir)
    results.from_env = helpers_store_parsers.parse_env(dirname, results.test_config, capture_state_dir)
    results.nodes_info = helpers_store_parsers.parse_nodes_info(dirname, capture_state_dir)
    results.cluster_info = helpers_store_parsers.extract_cluster_info(results.nodes_info)
    results.rhods_info = helpers_store_parsers.parse_rhods_info(dirname, artifact_paths.RHODS_CAPTURE_STATE, results.test_config.get("rhods.catalog.version_name"))

    results.test_start_end_time = _parse_start_end_time(dirname)

    results.sfttrainer_metrics = _parse_sfttrainer_logs(dirname)
    results.allocated_resources = _parse_allocated_resources(dirname)
    results.finish_reason = _parse_finish_reason(dirname)
    results.locations = _prepare_file_locations(dirname)
    results.job_config = _parse_job_config(dirname)
    results.tuning_config = _parse_tuning_config(dirname, results.locations.tuning_config_file)

@helpers_store_parsers.ignore_file_not_found
def _parse_start_end_time(dirname):
    ANSIBLE_LOG_TIME_FMT = '%Y-%m-%d %H:%M:%S'

    test_start_end_time = types.SimpleNamespace()
    test_start_end_time.start = None
    test_start_end_time.end = None

    if not artifact_paths.CLUSTER_CAPTURE_ENV_DIR:
        logging.warning("no capture_state_dir received. Cannot parse the test start/end times.")
        return test_start_end_time

    with open(register_important_file(dirname, artifact_paths.CLUSTER_CAPTURE_ENV_DIR / "_ansible.log")) as f:
        for line in f.readlines():
            time_str = line.partition(",")[0] # ignore the MS
            if test_start_end_time.start is None:
                test_start_end_time.start = datetime.datetime.strptime(time_str, ANSIBLE_LOG_TIME_FMT)
        if test_start_end_time.start is None:
            raise ValueError("Ansible log file is empty :/")

        test_start_end_time.end = datetime.datetime.strptime(time_str, ANSIBLE_LOG_TIME_FMT)

    return test_start_end_time

SFT_TRAINER_SUMMARY_KEYS = {
    "train_runtime": types.SimpleNamespace(lower_better=True, units="seconds", title="runtime"),
    "train_samples_per_second": types.SimpleNamespace(lower_better=False, units="samples/second"),
    "train_steps_per_second": types.SimpleNamespace(lower_better=False, units="steps/second"),
    "train_tokens_per_second": types.SimpleNamespace(lower_better=False, units="tokens/second"),
    "dataset_tokens_per_second": types.SimpleNamespace(lower_better=False, units="tokens/second", computed=True),
}

# dataset stats: {"total_tokens": 356, "total_samples": 10, "avg_tokens_per_sample": 36, "max_seq_token": 50}

DATASET_STATS_KEYS = [
    "total_tokens",
    "total_samples",
    "avg_tokens_per_sample",
    "max_seq_token",
]

SFT_TRAINER_PROGRESS_KEYS = {
    "loss": types.SimpleNamespace(lower_better=True, ),
    "grad_norm": types.SimpleNamespace(lower_better=True,),
    "learning_rate": types.SimpleNamespace(lower_better=False),
    "epoch": types.SimpleNamespace(plot=False),
}

@helpers_store_parsers.ignore_file_not_found
def _parse_sfttrainer_logs(dirname):
    sfttrainer_metrics = types.SimpleNamespace()
    sfttrainer_metrics.summary = types.SimpleNamespace()
    sfttrainer_metrics.progress = []
    sfttrainer_metrics.dataset_stats = types.SimpleNamespace()

    def parse_summary(key, data):
        summary = json.loads((key + data).replace("'", '"'))
        # {'train_runtime': 1.5203, 'train_samples_per_second': 6.578, 'train_steps_per_second': 0.658, 'train_tokens_per_second': 306.518, 'train_loss': 4.817451000213623, 'epoch': 1.0}

        # this will raise a KeyError if a key is missing in `summary`
        # this means that we are not parsing the data we're expecting.
        for key in SFT_TRAINER_SUMMARY_KEYS:
            if SFT_TRAINER_SUMMARY_KEYS[key].__dict__.get("computed", False): continue
            setattr(sfttrainer_metrics.summary, key, summary[key])

    def parse_progress(key, data):
        progress_json = json.loads((key + data).replace("'", '"'))
        # {'loss': 7.3438, 'grad_norm': 173.0, 'learning_rate': 9.755282581475769e-06, 'epoch': 1.0}

        # this will raise a KeyError if a key is missing in `results`
        # this means that we are not parsing the data we're expecting.
        progress = types.SimpleNamespace()
        for key in SFT_TRAINER_PROGRESS_KEYS:
            setattr(progress, key, progress_json[key])
        sfttrainer_metrics.progress.append(progress)

    def parse_dataset_stats(data):
        dataset_stats = json.loads(data)

        # this will raise a KeyError if a key is missing in `dataset_stats`
        # this means that we are not parsing the data we're expecting.
        for key in DATASET_STATS_KEYS:
            setattr(sfttrainer_metrics.dataset_stats, key, dataset_stats[key])


    with open(register_important_file(dirname, artifact_paths.FINE_TUNING_RUN_FINE_TUNING_DIR / "artifacts/pod.log")) as f:
        for line in f.readlines():
            _garbage, found_summary, line_data = line.strip().partition("{'train_runtime'")
            if found_summary:
                parse_summary(found_summary, line_data)

            _garbage, found_progress, line_data = line.strip().partition("{'loss'")
            if found_progress:
                parse_progress(found_progress, line_data)

            _garbage, found_dataset_stats, line_data = line.strip().partition("dataset stats: ")
            if found_dataset_stats:
                parse_dataset_stats(line_data)

    try:
        sfttrainer_metrics.summary.dataset_tokens_per_second = sfttrainer_metrics.dataset_stats.total_tokens / sfttrainer_metrics.summary.train_runtime
    except AttributeError as e:
        logging.warning(f"Could not compute 'dataset_tokens_per_second': {e}")

    return sfttrainer_metrics


def _parse_allocated_resources(dirname):
    allocated_resources = types.SimpleNamespace()
    with open(register_important_file(dirname, artifact_paths.FINE_TUNING_RUN_FINE_TUNING_DIR / "artifacts/pod.json")) as f:
        pod_def = json.load(f)

    try:
        allocated_resources.gpu = int(pod_def["items"][0]["spec"]["containers"][0]["resources"]["limits"]["nvidia.com/gpu"])
    except (IndexError, KeyError):
        allocated_resources.gpu = 0

    return allocated_resources


def _parse_finish_reason(dirname):
    finish_reason = types.SimpleNamespace()
    finish_reason.exit_code = None
    finish_reason.message = "Parsing did not complete"

    with open(register_important_file(dirname, artifact_paths.FINE_TUNING_RUN_FINE_TUNING_DIR / "artifacts/pod.json")) as f:
        pod_def = json.load(f)

    try:
        pod_status = pod_def["items"][0]["status"]
        container_status = pod_status["containerStatuses"]

        if container_terminated_state := container_status[0]["state"].get("terminated"):
            finish_reason.exit_code = container_terminated_state["exitCode"]
            finish_reason.message = container_terminated_state.get("message")
        else:
            finish_reason.exit_code = None
            finish_reason.message = "Container did not terminate"
    except (IndexError, KeyError) as e:
        finish_reason.exit_code = None
        finish_reason.message = "Couldn't locate the Pod/container status"

    return finish_reason


def _prepare_file_locations(dirname):
    locations = types.SimpleNamespace()

    locations.job_logs = artifact_paths.FINE_TUNING_RUN_FINE_TUNING_DIR / "artifacts/pod.log"
    job_logs_file = register_important_file(dirname, locations.job_logs)

    if not job_logs_file.exists():
        locations.job_logs = None
        logging.info(f"Job log file {job_logs_file} does not exist ...")

    locations.tuning_config_file = (job_logs_file.parent.parent / "src" / "config_final.json").relative_to(dirname)

    return locations


def _parse_job_config(dirname):
    job_config = {}

    PREFIX = "fine_tuning_run_fine_tuning_job_"

    with open(register_important_file(dirname, artifact_paths.FINE_TUNING_RUN_FINE_TUNING_DIR / "_ansible.play.yaml")) as f:
        ansible_play = yaml.safe_load(f)

    for k, v in ansible_play[0]["vars"].items():
        if not k.startswith(PREFIX): continue

        job_config[k.replace(PREFIX, "")] = v

    return job_config


def _parse_tuning_config(dirname, tuning_config_file_location):
    with open(register_important_file(dirname, tuning_config_file_location)) as f:
        tuning_config = json.load(f)

    return tuning_config
