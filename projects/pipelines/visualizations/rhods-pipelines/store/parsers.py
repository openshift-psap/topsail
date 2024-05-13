import types
import pathlib
import logging
import yaml
import os
import json
import datetime
from collections import defaultdict
import uuid

import jsonpath_ng

import matrix_benchmarking.cli_args as cli_args
import matrix_benchmarking.store.prom_db as store_prom_db

from . import prom as rhods_pipelines_prom

import projects.core.visualizations.helpers.store as core_helpers_store
import projects.core.visualizations.helpers.store.parsers as core_helpers_store_parsers

register_important_file = None # will be when importing store/__init__.py

artifact_dirnames = types.SimpleNamespace()
artifact_dirnames.LOCAL_CI__RUN_MULTI = "*__local_ci__run_multi"
artifact_dirnames.NOTEBOOKS_CAPTURE_STATE = "*__notebooks__capture_state"
artifact_paths = types.SimpleNamespace() # will be dynamically populated

IMPORTANT_FILES = [
    "artifacts_version",
    "config.yaml",

    f"{artifact_dirnames.LOCAL_CI__RUN_MULTI}/success_count",
    f"{artifact_dirnames.LOCAL_CI__RUN_MULTI}/ci_job.yaml",
    f"{artifact_dirnames.LOCAL_CI__RUN_MULTI}/prometheus_ocp.t*",

    f"{artifact_dirnames.LOCAL_CI__RUN_MULTI}/artifacts/ci-pod-*/progress_ts.yaml",
    f"{artifact_dirnames.LOCAL_CI__RUN_MULTI}/artifacts/ci-pod-*/test.exit_code",
    f"{artifact_dirnames.LOCAL_CI__RUN_MULTI}/artifacts/ci-pod-*/*/_ansible.log",
    f"{artifact_dirnames.LOCAL_CI__RUN_MULTI}/artifacts/ci-pod-*/*__pipelines__capture_state/pods/*.json",

    f"{artifact_dirnames.LOCAL_CI__RUN_MULTI}/artifacts/ci-pod-*/*__pipelines__capture_state/workflow.json",
    f"{artifact_dirnames.LOCAL_CI__RUN_MULTI}/artifacts/ci-pod-*/*__pipelines__capture_state/applications.json",
    f"{artifact_dirnames.LOCAL_CI__RUN_MULTI}/artifacts/ci-pod-*/*__pipelines__capture_state/deployments.json",
    f"{artifact_dirnames.LOCAL_CI__RUN_MULTI}/artifacts/ci-pod-*/*__pipelines__capture_state/pipelines.json",

    f"{artifact_dirnames.LOCAL_CI__RUN_MULTI}/artifacts/ci-pod-*/*__pipelines__run_kfp_notebook/notebook-artifacts/*_runs.json",

    f"{artifact_dirnames.NOTEBOOKS_CAPTURE_STATE}/nodes.json",
    f"{artifact_dirnames.NOTEBOOKS_CAPTURE_STATE}/ocp_version.yml",
    f"{artifact_dirnames.NOTEBOOKS_CAPTURE_STATE}/rhods.version",
    f"{artifact_dirnames.NOTEBOOKS_CAPTURE_STATE}/rhods.createdAt",
]

PARSER_VERSION = "2023-06-05"
ARTIFACTS_VERSION = "2023-06-05"

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
    results.from_local_env = core_helpers_store_parsers.parse_local_env(dirname)


def parse_once(results, dirname):
    results.test_config = core_helpers_store_parsers.parse_test_config(dirname)
    results.test_uuid = core_helpers_store_parsers.parse_test_uuid(dirname)

    results.user_count = int(results.test_config.get("tests.pipelines.user_count"))
    results.success_count = _parse_success_count(dirname)
    results.user_data = _parse_user_data(dirname, results.user_count)
    results.tester_job = _parse_tester_job(dirname)

    results.metrics = _extract_metrics(dirname)

    capture_state_dir = artifact_paths.NOTEBOOKS_CAPTURE_STATE
    results.ocp_version = core_helpers_store_parsers.parse_ocp_version(dirname, capture_state_dir)
    results.rhods_info = core_helpers_store_parsers.parse_rhods_info(dirname, capture_state_dir, results.test_config.get("rhods.catalog.version_name"))
    results.from_env = core_helpers_store_parsers.parse_env(dirname, results.test_config, capture_state_dir)
    results.nodes_info = core_helpers_store_parsers.parse_nodes_info(dirname, capture_state_dir)
    results.cluster_info = core_helpers_store_parsers.extract_cluster_info(results.nodes_info)


@ignore_file_not_found
def _parse_success_count(dirname):
    filename = pathlib.Path(f"{artifact_paths.LOCAL_CI__RUN_MULTI}") / "success_count"

    with open(register_important_file(dirname, filename)) as f:
        content = f.readline()

    success_count = int(content.split("/")[0])

    return success_count


@ignore_file_not_found
def _parse_user_exit_code(dirname, ci_pod_dir):
    filename = (ci_pod_dir / "test.exit_code").relative_to(dirname)
    with open(register_important_file(dirname, filename)) as f:
        exit_code = int(f.readline())

    return exit_code


@ignore_file_not_found
def _parse_user_progress(dirname, ci_pod_dir):
    filename = (ci_pod_dir / "progress_ts.yaml").relative_to(dirname)
    with open(register_important_file(dirname, filename)) as f:
        progress_src = yaml.safe_load(f)

    progress = {}
    for idx, (key, date_str) in enumerate(progress_src.items()):
        progress[f"progress_ts.{idx:03d}__{key}"] = datetime.datetime.strptime(date_str, core_helpers_store_parsers.SHELL_DATE_TIME_FMT)

    return progress


def _parse_user_ansible_progress(dirname, ci_pod_dir):
    ansible_progress = {}
    for ansible_log in sorted(ci_pod_dir.glob("*/_ansible.log")):
        filename = ansible_log.relative_to(dirname)
        last_line = None
        step_name = filename.parent.name
        with open(register_important_file(dirname, filename)) as f:
            for lines in f.readlines():
                last_line = lines
            if not last_line:
                logging.warning(f"Empty Ansible log file in {filename} :/")
                continue
            ts_str = last_line.split(",")[0]
            ts = datetime.datetime.strptime(ts_str, core_helpers_store_parsers.ANSIBLE_LOG_DATE_TIME_FMT)
            ansible_progress[f"ansible.{step_name}"] = ts

    return ansible_progress


def _parse_user_data(dirname, user_count):
    user_data = {}
    for user_id in range(user_count):
        ci_pod_dirname = dirname / f"{artifact_paths.LOCAL_CI__RUN_MULTI}" / "artifacts" / f"ci-pod-{user_id}"
        if not ci_pod_dirname.exists():
            user_data[user_id] = None
            logging.warning(f"No user directory collector for user #{user_id}")
            continue

        user_data[user_id] = data = types.SimpleNamespace()
        data.artifact_dir = ci_pod_dirname.relative_to(dirname)
        data.exit_code = _parse_user_exit_code(dirname, ci_pod_dirname)
        data.progress = _parse_user_progress(dirname, ci_pod_dirname)
        data.progress |= _parse_user_ansible_progress(dirname, ci_pod_dirname)

        data.resource_times = _parse_resource_times(dirname, ci_pod_dirname)
        data.pod_times = _parse_pod_times(dirname, ci_pod_dirname)
        data.workflow_run_names = _parse_workflow_run_names(dirname, ci_pod_dirname)
        data.workflow_start_times =  _parse_workflow_start_times(dirname, ci_pod_dirname)
        data.submit_run_times =  _parse_submit_run_times(dirname, ci_pod_dirname)


    return user_data


@ignore_file_not_found
def _parse_tester_job(dirname):
    job_info = types.SimpleNamespace()

    with open(register_important_file(dirname, f"{artifact_paths.LOCAL_CI__RUN_MULTI}/ci_job.yaml")) as f:
        job = yaml.safe_load(f)

    job_info.creation_time = \
        datetime.datetime.strptime(
            job["status"]["startTime"],
            core_helpers_store_parsers.K8S_TIME_FMT)

    if job["status"].get("completionTime"):
        job_info.completion_time = \
            datetime.datetime.strptime(
                job["status"]["completionTime"],
                core_helpers_store_parsers.K8S_TIME_FMT)
    else:
        job_info.completion_time = job_info.creation_time + datetime.timedelta(hours=1)

    if job["spec"]["template"]["spec"]["containers"][0]["name"] != "main":
        raise ValueError("Expected to find the 'main' container in position 0")

    job_info.env = {}
    for env in  job["spec"]["template"]["spec"]["containers"][0]["env"]:
        name = env["name"]
        value = env.get("value")
        if not value: continue

        job_info.env[name] = value

    return job_info


def _extract_metrics(dirname):
    db_files = {
        "sutest": (f"{artifact_paths.LOCAL_CI__RUN_MULTI}/prometheus_ocp.t*", rhods_pipelines_prom.get_sutest_metrics()),
        "driver": (f"{artifact_paths.LOCAL_CI__RUN_MULTI}/prometheus_ocp.t*", rhods_pipelines_prom.get_driver_metrics()),
        "dspa": (f"{artifact_paths.LOCAL_CI__RUN_MULTI}/prometheus_ocp.t*", rhods_pipelines_prom.get_dspa_metrics()),
    }

    return core_helpers_store_parsers.extract_metrics(dirname, db_files)


@ignore_file_not_found
def _parse_pod_times(dirname, ci_pod_dir):
    filenames = [fname.relative_to(dirname) for fname in
                 ci_pod_dir.glob("*__pipelines__capture_state/pods/*.json")]

    pod_times = []

    def _parse_pod_times_file(filename, pod):
        pod_time = types.SimpleNamespace()
        pod_times.append(pod_time)
        pod_time.is_pipeline_task = False
        pod_time.is_dspa = False
        pod_time.parent_workflow = ""

        if pod["metadata"]["labels"].get("component") == "data-science-pipelines":
            pod_friendly_name = pod["metadata"]["labels"]["app"]
            pod_time.is_dspa = True

        elif pod["metadata"]["labels"].get("pipelines.kubeflow.org/v2_component") == "true":
            pod_friendly_name = pod["metadata"]["name"]
            pod_time.parent_workflow = pod["metadata"]["labels"]["workflows.argoproj.io/workflow"]
            pod_time.is_pipeline_task = True

        elif pod["metadata"].get("generateName"):
            pod_friendly_name = pod["metadata"]["generateName"]\
                .replace("-"+pod["metadata"]["labels"].get("pod-template-hash", "")+"-", "")\
                .strip("-")

            if pod_friendly_name == "minio-deployment":
                pod_time.is_dspa = True
        else:
            pod_name = pod["metadata"]["name"]
            pod_friendly_name = pod_name

        pod_time.pod_name = pod["metadata"]["name"]
        pod_time.pod_friendly_name = pod_friendly_name
        pod_time.pod_namespace = pod["metadata"]["namespace"]
        pod_time.hostname = pod["spec"].get("nodeName")

        pod_time.creation_time = datetime.datetime.strptime(
                pod["metadata"]["creationTimestamp"], core_helpers_store_parsers.K8S_TIME_FMT)

        start_time_str = pod["status"].get("startTime")
        pod_time.start_time = None if not start_time_str else \
            datetime.datetime.strptime(start_time_str, core_helpers_store_parsers.K8S_TIME_FMT)

        for condition in pod["status"].get("conditions", []):
            last_transition = datetime.datetime.strptime(condition["lastTransitionTime"], core_helpers_store_parsers.K8S_TIME_FMT)

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
                    core_helpers_store_parsers.K8S_TIME_FMT)
            except KeyError: continue

            # take the last container_finished found
            if ("container_finished" not in pod_time.__dict__
                or pod_time.container_finished < finishedAt):
                pod_time.container_finished = finishedAt

        if "container_finished" not in pod_time.__dict__:
            pod_time.container_finished = False

    for filename in filenames:
        with open(register_important_file(dirname, filename)) as f:
            try:
                json_file = json.load(f)
            except Exception as e:
                if (dirname/filename).stat().st_size == 0:
                    logging.warning(f"File '{filename}' is empty")
                    continue
                logging.error(f"Couldn't parse JSON file '{filename}': {e}")
                continue

        try:
            _parse_pod_times_file(filename, json_file)
        except Exception as e:
            logging.error(f"Couldn't parse file '{filename}': {e.__class__.__name__}:{e}")

    return pod_times


def _parse_resource_times(dirname, ci_pod_dir):
    all_resource_times = {}
    logging.info(f"Parsing {ci_pod_dir.name} ...")

    @ignore_file_not_found
    def parse(fname):
        state_dirs = list(ci_pod_dir.glob("*__pipelines__capture_state"))
        if not state_dirs:
            logging.error(f"No '*__pipelines__capture_state' available in {dirname} ...")
            return

        file_path = (state_dirs[0] / fname).resolve().absolute().relative_to(dirname.absolute())
        with open(register_important_file(dirname, file_path)) as f:
            data = json.load(f)

        if type(data) is dict:
            data = [data]

        for entry in data:
            for item in entry["items"]:
                metadata = item["metadata"]

                kind = item["kind"]
                creationTimestamp = datetime.datetime.strptime(
                    metadata["creationTimestamp"], core_helpers_store_parsers.K8S_TIME_FMT)

                name = metadata["name"]
                generate_name, found, suffix = name.rpartition("-")
                remove_suffix = ((found and not suffix.isalpha()))

                if remove_suffix and kind != "Workflow":
                    name = generate_name # remove generated suffix

                all_resource_times[f"{kind}/{name}"] = creationTimestamp

    parse("applications.json")
    parse("deployments.json")
    parse("workflow.json")

    return dict(all_resource_times)

def _parse_workflow_run_names(dirname, ci_pod_dir):
    all_workflow_run_names = {}
    logging.info(f"Parsing {ci_pod_dir.name} ...")

    @ignore_file_not_found
    def parse(fname):
        state_dirs = list(ci_pod_dir.glob("*__pipelines__capture_state"))
        if not state_dirs:
            logging.error(f"No '*__pipelines__capture_state' available in {dirname} ...")
            return

        file_path = (state_dirs[0] / fname).resolve().absolute().relative_to(dirname.absolute())
        with open(register_important_file(dirname, file_path)) as f:
            data = json.load(f)

        if type(data) is dict:
            data = [data]

        for entry in data:
            for item in entry["items"]:
                metadata = item["metadata"]

                kind = item["kind"]
                creationTimestamp = datetime.datetime.strptime(
                    metadata["creationTimestamp"], core_helpers_store_parsers.K8S_TIME_FMT)

                name = metadata["name"]
                generate_name, found, suffix = name.rpartition("-")
                remove_suffix = ((found and not suffix.isalpha()))

                if remove_suffix and kind != "Workflow":
                    name = generate_name # remove generated suffix

                if kind == "Workflow":
                    all_workflow_run_names[f"{name}"] = metadata["annotations"]["pipelines.kubeflow.org/run_name"]

    parse("workflow.json")

    return dict(all_workflow_run_names)

def _parse_workflow_start_times(dirname, ci_pod_dir):
    """
    Measure the start time as .status.nodes[].startedAt where the .status.nodes[].templateName == 'root'
    This is the time that the first stage of the pipeline is started
    """
    all_workflow_start_times = {}
    logging.info(f"Parsing {ci_pod_dir.name} ...")

    @ignore_file_not_found
    def parse(fname):
        state_dirs = list(ci_pod_dir.glob("*__pipelines__capture_state"))
        if not state_dirs:
            logging.error(f"No '*__pipelines__capture_state' available in {dirname} ...")
            return

        file_path = (state_dirs[0] / fname).resolve().absolute().relative_to(dirname.absolute())
        with open(register_important_file(dirname, file_path)) as f:
            data = json.load(f)

        if type(data) is dict:
            data = [data]

        for entry in data:
            for item in entry["items"]:
                metadata = item["metadata"]
                status = item["status"]
                kind = item["kind"]
                creationTimestamp = datetime.datetime.strptime(
                    metadata["creationTimestamp"], core_helpers_store_parsers.K8S_TIME_FMT)

                name = metadata["name"]
                generate_name, found, suffix = name.rpartition("-")
                remove_suffix = ((found and not suffix.isalpha()))

                if remove_suffix and kind != "Workflow":
                    name = generate_name # remove generated suffix

                if kind == "Workflow":
                    root_node = {}
                    for node_name, node_spec in status["nodes"].items():
                        if node_spec["templateName"] == "root":
                            root_node = node_spec
                            break
                    all_workflow_start_times[f"{name}"] = datetime.datetime.strptime(
                        root_node["startedAt"], core_helpers_store_parsers.K8S_TIME_FMT)

    parse("workflow.json")

    return dict(all_workflow_start_times)

@ignore_file_not_found
def _parse_submit_run_times(dirname, ci_pod_dir):
    all_submit_run_times = {}
    logging.info(f"Parsing submit run times for {ci_pod_dir.name} ...")


    run_times_files = list(ci_pod_dir.glob("*__pipelines__run_kfp_notebook/notebook-artifacts/*_runs.json"))
    if not run_times_files:
        logging.error(f"No run times JSON files available in {dirname} ...")
        return

    paths = [run_times_file.resolve().absolute().relative_to(dirname.absolute()) for run_times_file in run_times_files]
    for path in paths:
        with open(register_important_file(dirname, path)) as f:
            data = json.load(f)

        for run_name, submit_time in data.items():
            # Drop all granularity finer than the second, since th K8S timestamps don't include it
            all_submit_run_times[run_name] = datetime.datetime.fromisoformat(submit_time).replace(microsecond=0)

    return dict(all_submit_run_times)
