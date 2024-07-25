import types
import pathlib
import logging
import yaml
import os
import json
import datetime
import urllib
import uuid
from collections import defaultdict
import re
import xmltodict

import jsonpath_ng

import matrix_benchmarking.cli_args as cli_args
import matrix_benchmarking.store.prom_db as store_prom_db

import projects.core.visualizations.helpers.store as core_helpers_store
import projects.core.visualizations.helpers.store.parsers as core_helpers_store_parsers
import projects.core.visualizations.helpers.store.k8s_quantity as k8s_quantity

from . import prom
from . import theoretical

register_important_file = None # will be when importing store/__init__.py

K8S_TIME_FMT = "%Y-%m-%dT%H:%M:%SZ"
SHELL_DATE_TIME_FMT = "%a %b %d %H:%M:%S %Z %Y"
ANSIBLE_LOG_DATE_TIME_FMT = "%Y-%m-%d %H:%M:%S"
ROBOT_TIME_FMT = "%Y%m%d %H:%M:%S.%f"

artifact_dirnames = types.SimpleNamespace()
artifact_dirnames.ARTIFACT_SUTEST_DIR = "artifacts-sutest"
artifact_dirnames.ARTIFACT_DRIVER_DIR = "artifacts-driver"

artifact_dirnames.CLUSTER_DUMP_PROM_DB_DIR = "artifacts-driver"

artifact_paths = types.SimpleNamespace() # will be dynamically populated


IMPORTANT_FILES = [
    "_ansible.env",
    ".uuid",

    f"{artifact_dirnames.ARTIFACT_SUTEST_DIR}/rhods.version",
    f"{artifact_dirnames.ARTIFACT_SUTEST_DIR}/rhods.createdAt",
    f"{artifact_dirnames.ARTIFACT_SUTEST_DIR}/odh-dashboard-config.yaml",
    f"{artifact_dirnames.ARTIFACT_SUTEST_DIR}/nodes.json",
    f"{artifact_dirnames.ARTIFACT_SUTEST_DIR}/ocp_version.yml",
    f"{artifact_dirnames.ARTIFACT_SUTEST_DIR}/prometheus_ocp.t*",
    f"{artifact_dirnames.ARTIFACT_SUTEST_DIR}/prometheus_rhods.t*",
    f"{artifact_dirnames.ARTIFACT_SUTEST_DIR}/project_*/notebook_pods.json",
    f"{artifact_dirnames.ARTIFACT_SUTEST_DIR}/project_*/notebooks.json",
    f"{artifact_dirnames.ARTIFACT_SUTEST_DIR}/project_*/namespaces.json",
    f"{artifact_dirnames.ARTIFACT_SUTEST_DIR}/routes.json",
    f"{artifact_dirnames.ARTIFACT_SUTEST_DIR}/services.json",
    f"{artifact_dirnames.ARTIFACT_SUTEST_DIR}/statefulsets.json",
    f"{artifact_dirnames.ARTIFACT_SUTEST_DIR}/secrets_safe.json",

    f"{artifact_dirnames.ARTIFACT_DRIVER_DIR}/nodes.json",
    f"{artifact_dirnames.ARTIFACT_DRIVER_DIR}/prometheus_ocp.t*",
    f"{artifact_dirnames.ARTIFACT_DRIVER_DIR}/tester_pods.json",
    f"{artifact_dirnames.ARTIFACT_DRIVER_DIR}/tester_job.yaml",
    "ods-ci/ods-ci-*/output.xml",
    "ods-ci/ods-ci-*/test.exit_code",
    "ods-ci/ods-ci-*/benchmark_measures.json",
    "ods-ci/ods-ci-*/progress_ts.yaml",
    "ods-ci/ods-ci-*/final_screenshot.png",
    "ods-ci/ods-ci-*/log.html",

    "notebook-artifacts/benchmark_measures.json",

    "src/000_rhods_notebook.yaml",

    "config.yaml",
]


JUPYTER_USER_RENAME_PREFIX = "jupyterhub-nb-user"

TEST_USERNAME_PREFIX = "psapuser"
JUPYTER_USER_IDX_REGEX = r'[:letter:]*(\d+)-0$'



def parse_always(results, dirname, import_settings):
    # parsed even when reloading from the cache file

    results.from_local_env = core_helpers_store_parsers.parse_local_env(dirname)
    pass



def parse_once(results, dirname):

    start_end = _parse_start_end_times(dirname)
    start, end = start_end if start_end else (None, None)
    results.start_time = start
    results.end_time = end

    results.test_config = core_helpers_store_parsers.parse_test_config(dirname)

    results.user_count = results.test_config.get("tests.notebooks.users.count")
    results.location = dirname

    results.test_uuid = core_helpers_store_parsers.parse_test_uuid(dirname)

    results.rhods_info = core_helpers_store_parsers.parse_rhods_info(dirname, artifact_paths.ARTIFACT_SUTEST_DIR, results.test_config.get("rhods.catalog.version_name"))
    results.ocp_version = core_helpers_store_parsers.parse_ocp_version(dirname, artifact_paths.ARTIFACT_SUTEST_DIR)
    results.from_env = core_helpers_store_parsers.parse_env(dirname, results.test_config, artifact_paths.ARTIFACT_SUTEST_DIR.parent)
    results.nodes_info = core_helpers_store_parsers.parse_nodes_info(dirname, artifact_paths.ARTIFACT_SUTEST_DIR)
    results.cluster_info = core_helpers_store_parsers.extract_cluster_info(results.nodes_info)

    results.metrics = _extract_metrics(dirname)

    # ---

    results.tester_job = _parse_tester_job(dirname)

    results.from_pr = _parse_pr(dirname)
    results.pr_comments = _parse_pr_comments(dirname)

    print("_parse_odh_dashboard_config")

    notebook_size_name = results.tester_job.env.get("NOTEBOOK_SIZE_NAME") if results.tester_job else None
    results.odh_dashboard_config = _parse_odh_dashboard_config(dirname, notebook_size_name)


    print("_parse_pod_times (tester)")

    results.testpod_times, results.testpod_hostnames = _parse_pod_times(dirname, results.test_config) or ({}, {})
    print("_parse_pod_times (notebooks)")
    results.notebook_pod_times, results.notebook_hostnames = _parse_pod_times(dirname, is_notebook=True) or ({}, {})

    print("_parse_notebook_times")
    _parse_notebook_times(dirname, results.notebook_pod_times)

    print("_parse_pod_results")

    # ODS-CI
    if (dirname / "ods-ci").exists():
        results.ods_ci = {}

        for ods_ci_dirname in (dirname / pathlib.Path("ods-ci")).glob("*"):
            pod_hostname = ods_ci_dirname.name
            user_idx = int(pod_hostname.split("-")[-1])
            output_dir = pathlib.Path("ods-ci") / pod_hostname
            results.ods_ci[user_idx] = _parse_ods_ci_pods_directory(dirname, output_dir) \
                if (dirname / output_dir).exists() else None
    else:
        results.ods_ci = None

    # notebook performance
    if (dirname / "notebook-artifacts").exists():
        if results.ods_ci is None:
            results.ods_ci = defaultdict(types.SimpleNamespace)
        ods_ci = results.ods_ci[-1] = types.SimpleNamespace()
        ods_ci.notebook_benchmark = _parse_notebook_benchmark(dirname, pathlib.Path("notebook-artifacts"))

    results.possible_machines = theoretical.get_possible_machines()

    results.notebook_perf = _parse_notebook_perf_notebook(dirname)

    results.all_resource_times = _parse_resource_times(dirname)


def _parse_ods_ci_pods_directory(dirname, output_dir):
    ods_ci = types.SimpleNamespace()

    ods_ci.output = _parse_ods_ci_output_xml(dirname, output_dir) or {}
    ods_ci.exit_code = _parse_ods_ci_exit_code(dirname, output_dir)
    ods_ci.notebook_benchmark = _parse_notebook_benchmark(dirname, output_dir)
    ods_ci.progress = _parse_ods_ci_progress(dirname, output_dir)

    return ods_ci


@core_helpers_store_parsers.ignore_file_not_found
def _parse_start_end_times(dirname):
    ISO_FORMAT="%Y-%m-%d %H:%M:%S"
    with open(dirname / '_ansible.log', 'r') as file:
        first = None
        last = None
        for line in file:
            if not first:
                first = line
            last = line

        # first = "2023-04-14 17:19:19,808 p=770 u=psap-ci-runner n=ansible | ansible-playbook 2.9.27"
        start_time = datetime.datetime.strptime(
            first.partition(',')[0],
            ISO_FORMAT
        )
        # last = 2023-04-14 17:25:31,697 p=770 u=psap-ci-runner n=ansible |...
        end_time = datetime.datetime.strptime(
            last.partition(',')[0],
            ISO_FORMAT
        )
        logging.debug(f'Start time: {start_time}')
        logging.debug(f'End time: {end_time}')

        return (start_time, end_time)

@core_helpers_store_parsers.ignore_file_not_found
def _parse_pr(dirname):
    with open(dirname.parent / "pull_request.json") as f: # not an important file
        return json.load(f)


@core_helpers_store_parsers.ignore_file_not_found
def _parse_pr_comments(dirname):
    with open(dirname.parent / "pull_request-comments.json") as f: # not an important file
        return json.load(f)


@core_helpers_store_parsers.ignore_file_not_found
def _parse_tester_job(dirname):
    job_info = types.SimpleNamespace()

    with open(register_important_file(dirname, pathlib.Path("artifacts-driver") / "tester_job.yaml")) as f:
        job = yaml.safe_load(f)

    job_info.creation_time = \
        datetime.datetime.strptime(
            job["status"]["startTime"],
            K8S_TIME_FMT)

    if job["status"].get("completionTime"):
        job_info.completion_time = \
            datetime.datetime.strptime(
                job["status"]["completionTime"],
                K8S_TIME_FMT)
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

    job_info.request = types.SimpleNamespace()
    rq = job["spec"]["template"]["spec"]["containers"][0]["resources"]["requests"]

    job_info.request.cpu = float(k8s_quantity.parse_quantity(rq["cpu"]))
    job_info.request.mem = float(k8s_quantity.parse_quantity(rq["memory"]) / 1024 / 1024 / 1024)

    return job_info


@core_helpers_store_parsers.ignore_file_not_found
def _parse_odh_dashboard_config(dirname, notebook_size_name):
    odh_dashboard_config = types.SimpleNamespace()
    odh_dashboard_config.path = None

    filename = pathlib.Path("artifacts-sutest") / "odh-dashboard-config.yaml"
    with open(register_important_file(dirname, filename)) as f:
        odh_dashboard_config.content = yaml.safe_load(f)

    if not odh_dashboard_config.content:
        return None

    odh_dashboard_config.path = str(filename)
    odh_dashboard_config.notebook_size_name = notebook_size_name
    odh_dashboard_config.notebook_request_size_mem = None
    odh_dashboard_config.notebook_request_size_cpu = None
    odh_dashboard_config.notebook_limit_size_mem = None
    odh_dashboard_config.notebook_limit_size_cpu = None

    for notebook_size in odh_dashboard_config.content["spec"]["notebookSizes"]:
        if notebook_size["name"] != odh_dashboard_config.notebook_size_name: continue

        odh_dashboard_config.notebook_request_size_mem = float(k8s_quantity.parse_quantity(notebook_size["resources"]["requests"]["memory"]) / 1024 / 1024 / 1024)
        odh_dashboard_config.notebook_request_size_cpu = float(k8s_quantity.parse_quantity(notebook_size["resources"]["requests"]["cpu"]))

        odh_dashboard_config.notebook_limit_size_mem = float(k8s_quantity.parse_quantity(notebook_size["resources"]["limits"]["memory"]) / 1024 / 1024 / 1024)
        odh_dashboard_config.notebook_limit_size_cpu = float(k8s_quantity.parse_quantity(notebook_size["resources"]["limits"]["cpu"]))

    return odh_dashboard_config




def _parse_resource_times(dirname):
    all_resource_times = defaultdict(dict)

    @core_helpers_store_parsers.ignore_file_not_found
    def parse(fname):
        print(f"Parsing {fname} ...")

        file_path = (dirname / "artifacts-sutest" / "project_dsg"/ f"{fname}.json").relative_to(dirname)
        with open(register_important_file(dirname, file_path)) as f:
            data = json.load(f)

        for item in data["items"]:

            metadata = item["metadata"]
            if fname == "namespaces":
                namespace = metadata["name"]
            else:
                namespace = metadata["namespace"]

            if not namespace.startswith(TEST_USERNAME_PREFIX): continue
            user_idx = int(namespace.replace(TEST_USERNAME_PREFIX, ""))

            kind = item["kind"]
            creationTimestamp = datetime.datetime.strptime(
                metadata["creationTimestamp"], K8S_TIME_FMT)

            name = metadata["name"].replace(namespace, "username")
            generate_name, found, suffix = name.rpartition("-")
            remove_suffix = ((found and not suffix.isalpha())
                             or "dockercfg" in name
                             or "token" in name)
            if remove_suffix:
                name = generate_name # remove generated suffix

            all_resource_times[f"{kind}/{name}"][user_idx] = creationTimestamp

    parse("notebook_pods")
    parse("notebooks")
    parse("namespaces")

    parse("../statefulsets")
    parse("../routes")
    parse("../services")
    parse("../secrets_safe")

    return dict(all_resource_times)


@core_helpers_store_parsers.ignore_file_not_found
def _parse_notebook_times(dirname, pod_times):
    filenames = [fname.relative_to(dirname) for fname in
                 (dirname / pathlib.Path("artifacts-sutest")).glob("project_*/notebooks.json")]

    def _parse_notebook_times_file(notebooks):
        for notebook in notebooks["items"]:
            notebook_name = notebook["metadata"]["name"]
            try:
                user_index = int(re.findall(JUPYTER_USER_IDX_REGEX, notebook_name + "-0")[0])
            except Exception as e:
                logging.warning(f"Cannot parsr user index in {notebook_name}")
                user_index = -1

            if user_index not in pod_times:
                continue

            pod_times[user_index].last_activity = None

            try:
                last_activity_str = notebook["metadata"]["annotations"]["notebooks.kubeflow.org/last-activity"]
            except KeyError:
                continue

            if not last_activity_str or not last_activity_str.endswith("Z"):
                continue

            last_activity = datetime.datetime.strptime(last_activity_str, K8S_TIME_FMT)
            pod_times[user_index].last_activity = last_activity


    for filename in filenames:
        with open(register_important_file(dirname, filename)) as f:
            _parse_notebook_times_file(json.load(f))

@core_helpers_store_parsers.ignore_file_not_found
def _parse_pod_times(dirname, test_config=None, is_notebook=False):
    if is_notebook:
        filenames = [fname.relative_to(dirname) for fname in
                     (dirname / pathlib.Path("artifacts-sutest")).glob("project_*/notebook_pods.json")]
    else:
        filenames = [pathlib.Path("artifacts-driver") / "tester_pods.json"]

    pod_times = defaultdict(types.SimpleNamespace)
    hostnames = {}

    def _parse_pod_times_file(pods):
        for pod in pods["items"]:
            pod_name = pod["metadata"]["name"]

            if is_notebook:
                if TEST_USERNAME_PREFIX not in pod_name:
                    continue

                user_index = re.findall(JUPYTER_USER_IDX_REGEX, pod_name)[0]
            elif "ods-ci-" in pod_name:
                user_index = int(pod_name.rpartition("-")[0].replace("ods-ci-", "")) \
                    - test_config.get("tests.notebooks.users.start_offset")
            else:
                logging.warning(f"Unexpected pod name: {pod_name}")
                continue

            user_index = int(user_index)
            pod_times[user_index].user_index = int(user_index)
            pod_times[user_index].pod_name = pod_name

            hostnames[user_index] = pod["spec"].get("nodeName")

            start_time = pod["status"].get("startTime")
            pod_times[user_index].start_time = None if not start_time else \
                datetime.datetime.strptime(start_time, K8S_TIME_FMT)

            for condition in pod["status"].get("conditions", []):
                last_transition = datetime.datetime.strptime(condition["lastTransitionTime"], K8S_TIME_FMT)

                if condition["type"] == "ContainersReady":
                    pod_times[user_index].containers_ready = last_transition

                elif condition["type"] == "Initialized":
                    pod_times[user_index].pod_initialized = last_transition
                elif condition["type"] == "PodScheduled":
                    pod_times[user_index].pod_scheduled = last_transition

            for containerStatus in pod["status"].get("containerStatuses", []):
                try:
                    finishedAt =  datetime.datetime.strptime(
                        containerStatus["state"]["terminated"]["finishedAt"],
                        K8S_TIME_FMT)
                except KeyError: continue

                if ("container_finished" not in pod_times[user_index].__dict__
                    or pod_times[user_index].container_finished < finishedAt):
                    pod_times[user_index].container_finished = finishedAt

    for filename in filenames:
        with open(register_important_file(dirname, filename)) as f:
            _parse_pod_times_file(json.load(f))

    return pod_times, hostnames

@core_helpers_store_parsers.ignore_file_not_found
def _parse_notebook_perf_notebook(dirname):
    notebook_perf = types.SimpleNamespace()

    filename = pathlib.Path("src") / "000_rhods_notebook.yaml"
    with open(register_important_file(dirname, filename)) as f:
        notebook_perf.notebook = yaml.safe_load(f)

    return notebook_perf

def _parse_test_config(dirname):
    test_config = types.SimpleNamespace()

    filename = pathlib.Path("config.yaml")
    test_config.filepath = dirname / filename

    with open(register_important_file(dirname, filename)) as f:
        yaml_file = test_config.yaml_file = yaml.safe_load(f)

    if not yaml_file:
        logging.error("Config file '{filename}' is empty ...")
        yaml_file = test_config.yaml_file = {}

    def get(key, missing=...):
        nonlocal yaml_file
        jsonpath_expression = jsonpath_ng.parse(f'$.{key}')

        match = jsonpath_expression.find(yaml_file)
        if not match:
            if missing != ...:
                return missing

            raise KeyError(f"Key '{key}' not found in {filename} ...")

        return match[0].value

    test_config.get = get

    return test_config

def _extract_metrics(dirname):
    db_files = {
        "sutest": (str(artifact_paths.CLUSTER_DUMP_PROM_DB_DIR / "prometheus_ocp.t*"), prom.get_sutest_metrics()),
        "driver": (str(artifact_paths.CLUSTER_DUMP_PROM_DB_DIR / "prometheus_ocp.t*"), prom.get_driver_metrics()),
        "rhods":  (str(artifact_paths.CLUSTER_DUMP_PROM_DB_DIR / "prometheus_rhods.t*"), prom.get_rhods_metrics()),
    }

    return core_helpers_store_parsers.extract_metrics(dirname, db_files)

@core_helpers_store_parsers.ignore_file_not_found
def _parse_ods_ci_exit_code(dirname, output_dir):
    filename = output_dir / "test.exit_code"

    with open(register_important_file(dirname, filename)) as f:
        code = f.read()
        if not code:
            return None

        try:
            return int(code)
        except ValueError as e:
            logging.warning(f"Failed to parse {filename}: {e}")
            return None

@core_helpers_store_parsers.ignore_file_not_found
def _parse_ods_ci_output_xml(dirname, output_dir):
    filename = output_dir / "output.xml"
    with open(register_important_file(dirname, filename)) as f:
        try:
            output_dict = xmltodict.parse(f.read())
        except Exception as e:
            logging.warning(f"Failed to parse {filename}: {e}")
            return None

    ods_ci_output = {}
    tests = output_dict["robot"]["suite"]["test"]
    if not isinstance(tests, list): tests = [tests]

    for test in tests:
        if test["status"].get("#text") == 'Failure occurred and exit-on-failure mode is in use.':
            continue

        ods_ci_output[test["@name"]] = output_step = types.SimpleNamespace()

        output_step.start = datetime.datetime.strptime(test["status"]["@starttime"], ROBOT_TIME_FMT)
        output_step.finish = datetime.datetime.strptime(test["status"]["@endtime"], ROBOT_TIME_FMT)
        output_step.status = test["status"]["@status"]

    return ods_ci_output


@core_helpers_store_parsers.ignore_file_not_found
def _parse_notebook_benchmark(dirname, output_dir):
    filename = output_dir / "benchmark_measures.json"
    with open(register_important_file(dirname, filename)) as f:
        return json.load(f)


@core_helpers_store_parsers.ignore_file_not_found
def _parse_ods_ci_progress(dirname, output_dir):
    filename = output_dir / "progress_ts.yaml"
    with open(register_important_file(dirname, filename)) as f:
        progress = yaml.safe_load(f)

    for key, date_str in progress.items():
        progress[key] = datetime.datetime.strptime(date_str, SHELL_DATE_TIME_FMT)

    return progress
