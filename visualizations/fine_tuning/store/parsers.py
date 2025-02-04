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

from . import FLAVOR, RAY_FLAVOR, FMS_FLAVOR, ILAB_FLAVOR

register_important_file = None # will be when importing store/__init__.py

K8S_TIME_FMT = "%Y-%m-%dT%H:%M:%SZ"
SHELL_DATE_TIME_FMT = "%a %b %d %H:%M:%S %Z %Y"
ANSIBLE_LOG_DATE_TIME_FMT = "%Y-%m-%d %H:%M:%S"

artifact_dirnames = types.SimpleNamespace()
artifact_dirnames.CLUSTER_CAPTURE_ENV_DIR = "*__cluster__capture_environment"

if FLAVOR in (FMS_FLAVOR, ILAB_FLAVOR):
    artifact_dirnames.FINE_TUNING_RUN_FINE_TUNING_DIR = "*__fine_tuning__run_fine_tuning_job"
elif FLAVOR == RAY_FLAVOR:
    artifact_dirnames.FINE_TUNING_RAY_FINE_TUNING_DIR = "*__fine_tuning__ray_fine_tuning_job"
artifact_dirnames.RHODS_CAPTURE_STATE = "*__rhods__capture_state"
artifact_paths = types.SimpleNamespace() # will be dynamically populated

IMPORTANT_FILES = [
    ".uuid",
    "config.yaml",
    f"{artifact_dirnames.CLUSTER_CAPTURE_ENV_DIR}/_ansible.log",
    f"{artifact_dirnames.CLUSTER_CAPTURE_ENV_DIR}/nodes.json",
    f"{artifact_dirnames.CLUSTER_CAPTURE_ENV_DIR}/ocp_version.yml",

    f"{artifact_dirnames.RHODS_CAPTURE_STATE}/rhods.createdAt",
    f"{artifact_dirnames.RHODS_CAPTURE_STATE}/rhods.version",
    f"{artifact_dirnames.CLUSTER_CAPTURE_ENV_DIR}/_ansible.env",
]

if FLAVOR in (FMS_FLAVOR, ILAB_FLAVOR):
    IMPORTANT_FILES += [
        f"{artifact_dirnames.FINE_TUNING_RUN_FINE_TUNING_DIR}/src/config_final.json",
        f"{artifact_dirnames.FINE_TUNING_RUN_FINE_TUNING_DIR}/artifacts/pod.log",
        f"{artifact_dirnames.FINE_TUNING_RUN_FINE_TUNING_DIR}/artifacts/pod.json",
        f"{artifact_dirnames.FINE_TUNING_RUN_FINE_TUNING_DIR}/_ansible.play.yaml",
    ]
elif FLAVOR == RAY_FLAVOR:
    IMPORTANT_FILES += [
        f"{artifact_dirnames.FINE_TUNING_RAY_FINE_TUNING_DIR}/src/config_final.json",
        f"{artifact_dirnames.FINE_TUNING_RAY_FINE_TUNING_DIR}/artifacts/job_pod.log",
        f"{artifact_dirnames.FINE_TUNING_RAY_FINE_TUNING_DIR}/_ansible.play.yaml",
    ]

def parse_always(results, dirname, import_settings):
    # parsed even when reloading from the cache file
    results.from_local_env = helpers_store_parsers.parse_local_env(dirname)

    pass


def parse_once(results, dirname, import_settings):
    results.test_config = helpers_store_parsers.parse_test_config(dirname)
    results.test_uuid = helpers_store_parsers.parse_test_uuid(dirname)

    capture_state_dir = artifact_paths.CLUSTER_CAPTURE_ENV_DIR
    results.ocp_version = helpers_store_parsers.parse_ocp_version(dirname, capture_state_dir)
    results.from_env = helpers_store_parsers.parse_env(dirname, results.test_config, capture_state_dir)
    results.nodes_info = helpers_store_parsers.parse_nodes_info(dirname, capture_state_dir)
    results.cluster_info = helpers_store_parsers.extract_cluster_info(results.nodes_info)
    results.rhods_info = helpers_store_parsers.parse_rhods_info(dirname, artifact_paths.RHODS_CAPTURE_STATE, results.test_config.get("rhods.catalog.version_name"))

    results.test_start_end_time = _parse_start_end_time(dirname)

    results.locations = _prepare_file_locations(dirname)

    results.job_config = _parse_job_config(dirname, results.locations)

    results.workload_config = _parse_workload_config(dirname, results.locations)

    if results.locations.has_fms:
        results.sfttrainer_metrics = _parse_fms_logs(dirname)

    if results.locations.has_ilab:
        results.ilab_metrics = _parse_ilab_logs(dirname)

    if results.locations.has_fms or results.locations.has_ilab:
        results.allocated_resources = _parse_pytorch_allocated_resources(dirname)
        results.finish_reason = _parse_pytorch_finish_reason(dirname)

    if results.locations.has_ray:
        flavor = results.job_config["hyper_parameters"].get("flavor")
        if flavor:
            results.ray_metrics = _parse_ray_logs(dirname, flavor)
        else:
            logging.error("Couldn't find the Ray test flavor in hyper_parameters.flavor, cannot parse the Ray logs")

        results.allocated_resources = _parse_ray_allocated_resources(dirname)
        results.finish_reason = _parse_ray_finish_reason(dirname)


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
def _parse_fms_logs(dirname):
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


ILAB_PROGRESS_KEYS = {
    "overall_throughput": types.SimpleNamespace(lower_better=False, units="samples/second", title="Throughput"),
    "cuda_mem_allocated": types.SimpleNamespace(lower_better=True, units="Gi", title="GPU Memory used (on 1 GPU)"),
    "lr": types.SimpleNamespace(lower_better=None, title="Learning rate", units=""),
    "total_loss": types.SimpleNamespace(lower_better=None, title="Training loss", units=""),
    "batch_size": types.SimpleNamespace(lower_better=None, title="Effective batch size", units=""),
}

ILAB_SUMMARY_KEYS = {
    "torchrun_exec_time": types.SimpleNamespace(lower_better=True, units="minutes", title="Execution wall-time"),
    "average_throughput": types.SimpleNamespace(lower_better=False, units="samples/second", title="Average throughput"),
}

"""
{
    "epoch": 6,
    "step": 7,
    "rank": 0,
    "overall_throughput": 6.080472087782912,
    "lr": 0.0,
    "cuda_mem_allocated": 1.8076796531677246,
    "cuda_malloc_retries": 0,
    "num_loss_counted_tokens": 74968,
    "batch_size": 55,
    "total_loss": 200.84430690427916,
    "samples_seen": 391,
    "timestamp": "2024-11-16T07:06:54.421224"
}
"""

@helpers_store_parsers.ignore_file_not_found
def _parse_ilab_logs(dirname):
    ilab_metrics = types.SimpleNamespace()
    ilab_metrics.summary = types.SimpleNamespace()
    ilab_metrics.progress = []
    ilab_metrics.dataset_stats = types.SimpleNamespace()

    def extract_torchrun_execution_time(line):
        if not line.startswith("TORCHRUN"):
            return

        _not_used, has_it, after = line.partition("TORCHRUN FINISHED after ")
        if not has_it: return

        time_str, has_it, after = after.partition(" seconds |")
        if not has_it:
            log.error(f"Invalid TORCHRUN FINISH line :/ '{line}'")
            return

        ilab_metrics.summary.torchrun_exec_time = int(time_str) / 60 # convert from seconds to minutes

    with (open(register_important_file(dirname, artifact_paths.FINE_TUNING_RUN_FINE_TUNING_DIR / "artifacts/pod.log")) as f):
        # metrics lines are printed in green. Look them up.
        in_green = False
        current_json = ""
        for line in f.readlines():
            extract_torchrun_execution_time(line)

            if not in_green:
                before, green_found, after = line.partition("[92m")
                if not green_found:
                    continue
                in_green = True
                line = after

            before, white_found, after = line.partition("[0m")
            if not white_found:
                current_json += line
                continue

            current_json += before[:-1] # remove the trailing ^[ char ...
            progress = types.SimpleNamespace()
            progress.__dict__.update(json.loads(current_json))
            ilab_metrics.progress.append(progress)
            current_json = ""
            in_green = False

        if ilab_metrics.progress:
            first_step_timestamp = datetime.datetime.fromisoformat(ilab_metrics.progress[0].timestamp)
            last_step_timestamp = datetime.datetime.fromisoformat(ilab_metrics.progress[-1].timestamp)
            first_step_samples_seen = ilab_metrics.progress[0].samples_seen
            last_step_samples_seen = ilab_metrics.progress[-1].samples_seen
            period = (last_step_timestamp - first_step_timestamp).total_seconds()
            all_samples_seen = last_step_samples_seen - first_step_samples_seen
            if period == 0: period = 1 # avoid /0 if there's only one step (in the smoke test)
            average_throughput = all_samples_seen/period
            ilab_metrics.summary.average_throughput = average_throughput

    return ilab_metrics


@helpers_store_parsers.ignore_file_not_found
def _parse_pytorch_allocated_resources(dirname):
    allocated_resources = types.SimpleNamespace()
    with open(register_important_file(dirname, artifact_paths.FINE_TUNING_RUN_FINE_TUNING_DIR / "artifacts/pod.json")) as f:
        pod_def = json.load(f)

    try:
        allocated_resources.gpu = int(pod_def["items"][0]["spec"]["containers"][0]["resources"]["limits"]["nvidia.com/gpu"])
    except (IndexError, KeyError):
        allocated_resources.gpu = 0

    return allocated_resources


@helpers_store_parsers.ignore_file_not_found
def _parse_ray_allocated_resources(dirname):
    pass


@helpers_store_parsers.ignore_file_not_found
def _parse_pytorch_finish_reason(dirname):
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


@helpers_store_parsers.ignore_file_not_found
def _parse_ray_finish_reason(dirname):
    finish_reason = types.SimpleNamespace()
    finish_reason.exit_code = None
    finish_reason.message = "_parse_ray_finish_reason: not implemented"

    return finish_reason


def _prepare_file_locations(dirname):
    locations = types.SimpleNamespace()

    locations.has_fms = FLAVOR == FMS_FLAVOR
    locations.has_ray = FLAVOR == RAY_FLAVOR
    locations.has_ilab = FLAVOR == ILAB_FLAVOR

    if locations.has_fms or locations.has_ilab:
        locations.job_dir = artifact_paths.FINE_TUNING_RUN_FINE_TUNING_DIR
        locations.job_logs = artifact_paths.FINE_TUNING_RUN_FINE_TUNING_DIR / "artifacts/pod.log"

    elif locations.has_ray:
        locations.job_dir = artifact_paths.FINE_TUNING_RAY_FINE_TUNING_DIR
        locations.job_logs = artifact_paths.FINE_TUNING_RAY_FINE_TUNING_DIR / "artifacts/job_pod.log"
    else:
        logging.error("Couldn't find the FMS/Ray/Ilab job directory ...")
        locations.job_dir = None
        locations.job_logs = None

    job_logs_file = register_important_file(dirname, locations.job_logs)

    if not job_logs_file.exists():
        locations.job_logs = None
        logging.info(f"Job log file {job_logs_file} does not exist ...")

    locations.workload_config_file = locations.job_dir / "src" / "config_final.json"

    return locations


@helpers_store_parsers.ignore_file_not_found
def _parse_job_config(dirname, locations):
    job_config = {}

    if locations.has_fms or locations.has_ilab:
        prefix = "fine_tuning_run_fine_tuning_job_"
    elif locations.has_ray:
        prefix = "fine_tuning_ray_fine_tuning_job_"

    with open(register_important_file(dirname, locations.job_dir / "_ansible.play.yaml")) as f:
        ansible_play = yaml.safe_load(f)

    for k, v in ansible_play[0]["vars"].items():
        if not k.startswith(prefix): continue

        job_config[k.replace(prefix, "")] = v

    return job_config


@helpers_store_parsers.ignore_file_not_found
def _parse_workload_config(dirname, locations):
    with open(register_important_file(dirname, locations.workload_config_file)) as f:
        workload_config = json.load(f)

    return workload_config


@helpers_store_parsers.ignore_file_not_found
def _parse_ray_logs(dirname, flavor):
    ray_metrics = types.SimpleNamespace()

    ray_metrics.summary = types.SimpleNamespace()
    ray_metrics.progress = []

    with open(register_important_file(dirname, artifact_paths.FINE_TUNING_RAY_FINE_TUNING_DIR / "artifacts/job_pod.log")) as f:
        if flavor == "iperf":
            _parse_ray_logs__iperf(f, ray_metrics.summary, ray_metrics.progress)
        elif flavor == "network_overhead":
            _parse_ray_logs__network_overhead(f, ray_metrics.summary, ray_metrics.progress)
        else:
            msg = f"Benchmark flavor not recognized :/ ({flavor})"
            logging.fatal(msg)
            raise ValueError(msg)

    return ray_metrics


def _parse_ray_logs__iperf(f, summary, progress):
    seen_marker_line = 0
    for line in f.readlines():
        # [ ID] Interval           Transfer     Bitrate
        if line.startswith("[ ID] Interval"):
            seen_marker_line += 1
            continue
        if seen_marker_line != 2:
            continue

        # [  5]   0.00-10.04  sec  7.79 GBytes  6.66 Gbits/sec                  receiver
        summary.bitrate = float(line.split()[6])
        break

    pass


def _parse_ray_logs__network_overhead(f, summary, progress):
    for line in f.readlines():
        if not line.startswith("---"):
            continue
        summary.time = float(line.strip().split("::: ")[-1].split()[0])
        break
