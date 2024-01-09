import types
import pathlib
import yaml
import datetime
from collections import defaultdict
import xmltodict
import logging
import re
import os
import json
import fnmatch
import pickle

import pandas as pd
import jsonpath_ng

import matrix_benchmarking.store as store
import matrix_benchmarking.store.simple as store_simple
import matrix_benchmarking.common as common
import matrix_benchmarking.cli_args as cli_args
import matrix_benchmarking.store.prom_db as store_prom_db

import matrix_benchmarking.cli_args as cli_args


from . import models
from . import k8s_quantity
from . import store_theoretical
from . import store_thresholds
from .plotting import prom as rhods_plotting_prom
from . import lts_parser, lts

K8S_EVT_TIME_FMT = "%Y-%m-%dT%H:%M:%S.%fZ"
K8S_TIME_FMT = "%Y-%m-%dT%H:%M:%SZ"
ROBOT_TIME_FMT = "%Y%m%d %H:%M:%S.%f"
SHELL_DATE_TIME_FMT = "%a %b %d %H:%M:%S %Z %Y"

JUPYTER_USER_RENAME_PREFIX = "jupyterhub-nb-user"

TEST_USERNAME_PREFIX = "psapuser"
JUPYTER_USER_IDX_REGEX = r'[:letter:]*(\d+)-0$'

THIS_DIR = pathlib.Path(__file__).resolve().parent

CACHE_FILENAME = "cache.pickle"

IMPORTANT_FILES = [
    "_ansible.env",

    "artifacts-sutest/rhods.version",
    "artifacts-sutest/rhods.createdAt",
    "artifacts-sutest/odh-dashboard-config.yaml",
    "artifacts-sutest/nodes.json",
    "artifacts-sutest/ocp_version.yml",
    "artifacts-sutest/prometheus_ocp.t*",
    "artifacts-sutest/prometheus_rhods.t*",
    "artifacts-sutest/project_*/notebook_pods.json",
    "artifacts-sutest/project_*/notebooks.json",
    "artifacts-sutest/project_*/namespaces.json",
    "artifacts-sutest/routes.json",
    "artifacts-sutest/services.json",
    "artifacts-sutest/statefulsets.json",
    "artifacts-sutest/secrets_safe.json",

    "artifacts-driver/nodes.json",
    "artifacts-driver/prometheus_ocp.t*",
    "artifacts-driver/tester_pods.json",
    "artifacts-driver/tester_job.yaml",
    "ods-ci/ods-ci-*/output.xml",
    "ods-ci/ods-ci-*/test.exit_code",
    "ods-ci/ods-ci-*/benchmark_measures.json",
    "ods-ci/ods-ci-*/progress_ts.yaml",
    "ods-ci/ods-ci-*/final_screenshot.png",
    "ods-ci/ods-ci-*/log.html",

    "notebook-artifacts/benchmark_measures.json",

    "src/000_rhods_notebook.yaml",

    "metrics/*",

    "config.yaml",
]


ARTIFACTS_VERSION = "2022-11-09"
PARSER_VERSION = "2022-12-14"


store.register_lts_schema(models.NotebookScalePayload)

def is_mandatory_file(filename):
    return filename.name in ("settings", "exit_code", "config.yaml") or filename.name.startswith("settings.")


def is_important_file(filename):
    if str(filename) in IMPORTANT_FILES:
        return True

    for important_file in IMPORTANT_FILES:
        if "*" not in important_file: continue

        if fnmatch.filter([str(filename)], important_file):
            return True

    return False


def is_cache_file(filename):
    return filename.name == CACHE_FILENAME


def register_important_file(base_dirname, filename):
    if not is_important_file(filename):
        logging.warning(f"File '{filename}' not part of the important file list :/")

    return base_dirname / filename


def _rewrite_settings(settings_dict):
    try: del settings_dict["date"]
    except KeyError: pass

    try: del settings_dict["check_thresholds"]
    except KeyError: pass

    if "repeat" not in settings_dict:
        settings_dict["repeat"] = "1"

    if "live_users" in settings_dict:
        settings_dict["live_users"] = int(settings_dict["live_users"])

    if "users_already_in" in settings_dict:
        settings_dict["users_already_in"] = int(settings_dict["users_already_in"])

    if "user_count" in settings_dict:
        settings_dict["user_count"] = int(settings_dict["user_count"])

    if "launcher" in settings_dict:
        del settings_dict["test_case"]

    del settings_dict["expe"]

    if settings_dict.get("mode") == "notebook_perf":
        for k in ("image", "benchmark_name", "benchmark_repeat", "benchmark_number", "notebook_file_name", "instance_type", "exclude_tags", "test_case"):
            try: del settings_dict[k]
            except KeyError: pass

    return settings_dict

def ignore_file_not_found(fn):
    def decorator(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except FileNotFoundError as e:
            logging.warning(f"{fn.__name__}: FileNotFoundError: {e}")
            return None

    return decorator

@ignore_file_not_found
def _parse_artifacts_version(dirname):
    with open(dirname / "artifacts_version") as f:
        artifacts_version = f.read().strip()

    return artifacts_version

def _parse_local_env(dirname):
    from_local_env = types.SimpleNamespace()

    from_local_env.artifacts_basedir = None
    from_local_env.source_url = None
    from_local_env.is_interactive = False

    try:
        with open(dirname / "source_url") as f: # not an important file
            from_local_env.source_url = f.read().strip()
            from_local_env.artifacts_basedir = pathlib.Path(from_local_env.source_url.replace("https://gcsweb-ci.apps.ci.l2s4.p1.openshiftapps.com/", "/"))
    except FileNotFoundError as e:
        pass

    if not cli_args.kwargs.get("generate"):
        # running in interactive mode
        from_local_env.is_interactive = True
        from_local_env.artifacts_basedir = dirname
        return from_local_env

    # running in generate mode

    # This must be parsed from the process env (not the file), to
    # properly generate the error report links to the image.
    job_name = os.getenv("JOB_NAME_SAFE")

    if job_name == "plot-notebooks":
        # running independently of the test, the source_url file must be available
        if from_local_env.source_url is None:
            logging.warning(f"The source URL should be available when running from '{job_name}'")
            from_local_env.source_url = "/missing/source/url"
            from_local_env.artifacts_basedir = dirname

    elif "ARTIFACT_DIR" in os.environ:

        # os.path.relpath can return '..', but pathlib.Path().relative_to cannot
        from_local_env.source_url = pathlib.Path(os.path.relpath(dirname,
                                                                 pathlib.Path(os.environ["ARTIFACT_DIR"])))
        from_local_env.artifacts_basedir = from_local_env.source_url

    else:
        logging.error(f"Unknown execution environment: JOB_NAME_SAFE={job_name}")
        from_local_env.artifacts_basedir = dirname.absolute()

    return from_local_env


@ignore_file_not_found
def _parse_env(dirname):
    from_env = types.SimpleNamespace()

    from_env.env = {}
    from_env.pr = None
    with open(register_important_file(dirname, "_ansible.env")) as f:
        for line in f.readlines():
            k, _, v = line.strip().partition("=")

            from_env.env[k] = v

            if k != "JOB_SPEC": continue

            job_spec = json.loads(v)

            from_env.pr = pr = types.SimpleNamespace()
            pr.link = job_spec["refs"]["pulls"][0]["link"]
            pr.number = job_spec["refs"]["pulls"][0]["number"]
            pr.diff_link = "".join([
                job_spec["refs"]["repo_link"], "/compare/",
                job_spec["refs"]["base_sha"] + ".." + job_spec["refs"]["pulls"][0]["sha"]
            ])
            pr.base_link = "".join([
                job_spec["refs"]["repo_link"], "/tree/",
                job_spec["refs"]["base_sha"]
            ])
            pr.name = "".join([
                job_spec["refs"]["org"], "/", job_spec["refs"]["repo"], " ", f"#{pr.number}"
            ])
            pr.base_ref = job_spec["refs"]["base_ref"]

    from_env.ci_run = "JOB_NAME_SAFE" in from_env.env

    return from_env


@ignore_file_not_found
def _parse_pr(dirname):
    with open(dirname.parent / "pull_request.json") as f: # not an important file
        return json.load(f)


@ignore_file_not_found
def _parse_pr_comments(dirname):
    with open(dirname.parent / "pull_request-comments.json") as f: # not an important file
        return json.load(f)


@ignore_file_not_found
def _parse_rhods_info(dirname):
    rhods_info = types.SimpleNamespace()

    with open(register_important_file(dirname, pathlib.Path("artifacts-sutest") / "rhods.version")) as f:
        rhods_info.version = f.read().strip()

    with open(register_important_file(dirname, pathlib.Path("artifacts-sutest") / "rhods.createdAt")) as f:
        rhods_info.createdAt_raw = f.read().strip()

    try:
        rhods_info.createdAt = datetime.datetime.strptime(rhods_info.createdAt_raw, K8S_TIME_FMT)
    except ValueError as e:
        logging.error("Couldn't parse RHODS version timestamp: {e}")
        rhods_info.createdAt = None

    return rhods_info


@ignore_file_not_found
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


@ignore_file_not_found
def _parse_nodes_info(dirname, sutest_cluster=False):
    nodes_info = {}
    filename = pathlib.Path("artifacts-sutest" if sutest_cluster else "artifacts-driver") / "nodes.json"
    with open(register_important_file(dirname, filename)) as f:
        nodeList = json.load(f)

    for node in nodeList["items"]:
        node_name = node["metadata"]["name"]
        node_info = nodes_info[node_name] = types.SimpleNamespace()

        node_info.name = node_name
        node_info.sutest_cluster = sutest_cluster
        node_info.managed = "managed.openshift.com/customlabels" in node["metadata"]["annotations"]
        node_info.instance_type = node["metadata"]["labels"].get("node.kubernetes.io/instance-type", "N/A")

        node_info.control_plane = "node-role.kubernetes.io/control-plane" in node["metadata"]["labels"] or "node-role.kubernetes.io/master" in node["metadata"]["labels"]
        node_info.rhods_compute = node["metadata"]["labels"].get("only-rhods-compute-pods") == "yes"

        node_info.test_pods_only = node["metadata"]["labels"].get("only-test-pods") == "yes"
        node_info.infra = \
            not node_info.control_plane and \
            not node_info.rhods_compute and \
            not node_info.test_pods_only

    return nodes_info


@ignore_file_not_found
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

    @ignore_file_not_found
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


@ignore_file_not_found
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

@ignore_file_not_found
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

@ignore_file_not_found
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
    METRICS = {
        "sutest": ("artifacts-sutest/prometheus_ocp.t*", rhods_plotting_prom.get_sutest_metrics()),
        "driver": ("artifacts-driver/prometheus_ocp.t*", rhods_plotting_prom.get_driver_metrics()),
        "rhods":  ("artifacts-sutest/prometheus_rhods.t*", rhods_plotting_prom.get_rhods_metrics()),
    }

    results_metrics = {}
    for name, (tarball_glob, metrics) in METRICS.items():
        try:
            prom_tarball = list(dirname.glob(tarball_glob))[0]
        except IndexError:
            logging.warning(f"No {tarball_glob} in '{dirname}'.")
            continue

        register_important_file(dirname, prom_tarball.relative_to(dirname))
        results_metrics[name] = store_prom_db.extract_metrics(prom_tarball, metrics, dirname)

    return results_metrics


@ignore_file_not_found
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

@ignore_file_not_found
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


@ignore_file_not_found
def _parse_notebook_benchmark(dirname, output_dir):
    filename = output_dir / "benchmark_measures.json"
    with open(register_important_file(dirname, filename)) as f:
        return json.load(f)


@ignore_file_not_found
def _parse_ods_ci_progress(dirname, output_dir):
    filename = output_dir / "progress_ts.yaml"
    with open(register_important_file(dirname, filename)) as f:
        progress = yaml.safe_load(f)

    for key, date_str in progress.items():
        progress[key] = datetime.datetime.strptime(date_str, SHELL_DATE_TIME_FMT)

    return progress

@ignore_file_not_found
def _parse_ocp_version(dirname):
    with open(register_important_file(dirname, pathlib.Path("artifacts-sutest") / "ocp_version.yml")) as f:
        sutest_ocp_version_yaml = yaml.safe_load(f)

    return sutest_ocp_version_yaml["openshiftVersion"]

def _extract_rhods_cluster_info(nodes_info):
    rhods_cluster_info = types.SimpleNamespace()

    rhods_cluster_info.node_count = [node_info for node_info in nodes_info.values() \
                                     if node_info.sutest_cluster]

    rhods_cluster_info.control_plane = [node_info for node_info in nodes_info.values() \
                                 if node_info.sutest_cluster and node_info.control_plane]

    rhods_cluster_info.infra = [node_info for node_info in nodes_info.values() \
                                if node_info.sutest_cluster and node_info.infra]

    rhods_cluster_info.rhods_compute = [node_info for node_info in nodes_info.values() \
                                  if node_info.sutest_cluster and node_info.rhods_compute]

    rhods_cluster_info.test_pods_only = [node_info for node_info in nodes_info.values() if node_info.test_pods_only]

    return rhods_cluster_info


def _parse_always(results, dirname, import_settings):
    # parsed even when reloading from the cache file

    results.from_local_env = _parse_local_env(dirname)
    results.thresholds = store_thresholds.get_thresholds(import_settings)
    results.test_config = _parse_test_config(dirname)

    results.check_thresholds = import_settings.get("check_thresholds", "no") == "yes"
    if results.check_thresholds:
        if results.thresholds:
            logging.info(f"Check thresholds set for {dirname}")
            logging.info(f"Thresholds: {results.thresholds}")
        else:
            logging.error(f"Check thresholds set for {dirname}, but no threshold available {import_settings} :/")
            logging.info(f"Import settings: {import_settings}")


def load_cache(dirname):
    try:
        with open(dirname / CACHE_FILENAME, "rb") as f:
            results = pickle.load(f)

        cache_version = getattr(results, "parser_version", None)
        if cache_version != PARSER_VERSION:
            raise ValueError(cache_version)

    except ValueError as e:
        cache_version = e.args[0]
        if not cache_version:
            logging.warning(f"Cache file '{dirname / CACHE_FILENAME}' does not have a version, ignoring.")
        else:
            logging.warning(f"Cache file '{dirname / CACHE_FILENAME}' version '{cache_version}' does not match the parser version '{PARSER_VERSION}', ignoring.")

        results = None

    return results

def _parse_ods_ci_pods_directory(dirname, output_dir):
    ods_ci = types.SimpleNamespace()

    ods_ci.output = _parse_ods_ci_output_xml(dirname, output_dir) or {}
    ods_ci.exit_code = _parse_ods_ci_exit_code(dirname, output_dir)
    ods_ci.notebook_benchmark = _parse_notebook_benchmark(dirname, output_dir)
    ods_ci.progress = _parse_ods_ci_progress(dirname, output_dir)

    return ods_ci

def _parse_directory(fn_add_to_matrix, dirname, import_settings):

    try:
        results = load_cache(dirname)
    except FileNotFoundError:
        results = None # Cache file doesn't exit, ignore and parse the artifacts

    if results:
        _parse_always(results, dirname, import_settings)

        fn_add_to_matrix(results)

        return


    results = types.SimpleNamespace()

    results.parser_version = PARSER_VERSION
    results.artifacts_version = _parse_artifacts_version(dirname)

    if results.artifacts_version != ARTIFACTS_VERSION:
        if not results.artifacts_version:
            logging.warning("Artifacts does not have a version...")
        else:
            logging.warning(f"Artifacts version '{results.artifacts_version}' does not match the parser version '{ARTIFACTS_VERSION}' ...")

    _parse_always(results, dirname, import_settings)

    start_end = _parse_start_end_times(dirname)
    start, end = start_end if start_end else (None, None)
    results.start_time = start
    results.end_time = end

    results.user_count = int(import_settings.get("user_count", 0))
    results.location = dirname

    results.tester_job = _parse_tester_job(dirname)
    results.from_env = _parse_env(dirname)

    results.from_pr = _parse_pr(dirname)
    results.pr_comments = _parse_pr_comments(dirname)

    results.rhods_info = _parse_rhods_info(dirname)

    print("_parse_odh_dashboard_config")

    notebook_size_name = results.tester_job.env.get("NOTEBOOK_SIZE_NAME") if results.tester_job else None
    results.odh_dashboard_config = _parse_odh_dashboard_config(dirname, notebook_size_name)

    print("_parse_nodes_info")
    results.nodes_info = {}
    results.nodes_info |= _parse_nodes_info(dirname) or {}
    results.nodes_info |= _parse_nodes_info(dirname, sutest_cluster=True) or {}

    results.sutest_ocp_version = _parse_ocp_version(dirname)

    print("_extract_metrics")
    results.metrics = _extract_metrics(dirname)


    print("_parse_pod_times (tester)")

    results.testpod_times, results.testpod_hostnames = _parse_pod_times(dirname, results.test_config) or ({}, {})
    print("_parse_pod_times (notebooks)")
    results.notebook_pod_times, results.notebook_hostnames = _parse_pod_times(dirname, is_notebook=True) or ({}, {})

    print("_parse_notebook_times")
    _parse_notebook_times(dirname, results.notebook_pod_times)

    results.rhods_cluster_info = _extract_rhods_cluster_info(results.nodes_info)

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

    results.possible_machines = store_theoretical.get_possible_machines()

    results.notebook_perf = _parse_notebook_perf_notebook(dirname)

    results.all_resource_times = _parse_resource_times(dirname)

    results.lts = lts_parser.generate_lts_payload(results, import_settings)

    print("add the result to the matrix ...")

    fn_add_to_matrix(results)

    with open(dirname / CACHE_FILENAME, "wb") as f:
        get_config = results.test_config.get
        results.test_config.get = None

        pickle.dump(results, f)

        results.test_config.get = get_config

    print("parsing done :)")

@ignore_file_not_found
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


def parse_data():
    # delegate the parsing to the simple_store
    store.register_custom_rewrite_settings(_rewrite_settings)
    store_simple.register_custom_parse_results(_parse_directory)
    store_simple.register_custom_lts_parse_results(lts._parse_lts_dir)

    return store_simple.parse_data()

def build_lts_payloads():
    store_simple.register_custom_build_lts_payloads(lts.build_lts_payloads)

    return store_simple.build_lts_payloads()
