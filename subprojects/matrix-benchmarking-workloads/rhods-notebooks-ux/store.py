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

import matrix_benchmarking.store as store
import matrix_benchmarking.store.simple as store_simple
import matrix_benchmarking.common as common
import matrix_benchmarking.cli_args as cli_args
import matrix_benchmarking.store.prom_db as store_prom_db

import matrix_benchmarking.cli_args as cli_args

from . import k8s_quantity
from . import store_theoretical
from . import store_thresholds
from .plotting import prom as rhods_plotting_prom

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
    "artifacts-sutest/odh-dashboard-config.yaml",
    "artifacts-sutest/nodes.yaml",
    "artifacts-sutest/ocp_version.yml",
    "artifacts-sutest/prometheus_ocp.t*",
    "artifacts-sutest/prometheus_rhods.t*",
    "artifacts-sutest/notebook_pods.yaml",

    "artifacts-driver/nodes.yaml",
    "artifacts-driver/prometheus_ocp.t*",
    "artifacts-driver/tester_pods.yaml",
    "artifacts-driver/tester_job.yaml",
    "ods-ci/ods-ci-*/output.xml",
    "ods-ci/ods-ci-*/test.exit_code",
    "ods-ci/ods-ci-*/benchmark_measures.json",
    "ods-ci/ods-ci-*/progress_ts.yaml",
    "ods-ci/ods-ci-*/final_screenshot.png",
    "ods-ci/ods-ci-*/log.html",
]


ARTIFACTS_VERSION = "2022-10-18"
PARSER_VERSION = "2022-10-18"


def is_mandatory_file(filename):
    return filename.name in ("settings", "exit_code")


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
    if not cli_args.kwargs.get("generate"):
        # running in interactive mode
        from_local_env.is_interactive = True
        return from_local_env

    # running in generate mode

    # This must be parsed from the process env (not the file), to
    # properly generate the error report links to the image.
    job_name = os.getenv("JOB_NAME_SAFE")

    if not job_name or job_name == "plot-notebooks":
        # not running in the CI / running independently of the test
        try:
            with open(dirname / "source_url") as f: # not an important file
                from_local_env.source_url = f.read().strip()

            from_local_env.artifacts_basedir = pathlib.Path(from_local_env.source_url.replace("https://gcsweb-ci.apps.ci.l2s4.p1.openshiftapps.com/", "/"))
        except FileNotFoundError:
            from_local_env.source_url = "file-not-found"

    elif job_name == "notebooks" or job_name.startswith("notebooks-on-"):
        # running right after the test

        from_local_env.artifacts_basedir = pathlib.Path("..") / dirname.name

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

    from_env.single_cluster = "single" in from_env.env["JOB_NAME_SAFE"]

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
        job_info.completion_time = results.job_creation_time + datetime.timedelta(hours=1)

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
    filename = pathlib.Path("artifacts-sutest" if sutest_cluster else "artifacts-driver") / "nodes.yaml"
    with open(register_important_file(dirname, filename)) as f:
        nodeList = yaml.safe_load(f)

    for node in nodeList["items"]:
        node_name = node["metadata"]["name"]
        node_info = nodes_info[node_name] = types.SimpleNamespace()

        node_info.name = node_name
        node_info.sutest_cluster = sutest_cluster
        node_info.managed = "managed.openshift.com/customlabels" in node["metadata"]["annotations"]
        node_info.instance_type = node["metadata"]["labels"]["node.kubernetes.io/instance-type"]

        node_info.master = "node-role.kubernetes.io/master" in node["metadata"]["labels"]
        node_info.rhods_compute = node["metadata"]["labels"].get("only-rhods-compute-pods") == "yes"

        node_info.test_pods_only = node["metadata"]["labels"].get("only-test-pods") == "yes"
        node_info.infra = \
            not node_info.master and \
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

    odh_dashboard_config.path = str(filename)
    odh_dashboard_config.notebook_size_name = notebook_size_name
    odh_dashboard_config.notebook_size_mem = None
    odh_dashboard_config.notebook_size_cpu = None

    for notebook_size in odh_dashboard_config.content["spec"]["notebookSizes"]:
        if notebook_size["name"] != odh_dashboard_config.notebook_size_name: continue

        odh_dashboard_config.notebook_request_size_mem = float(k8s_quantity.parse_quantity(notebook_size["resources"]["requests"]["memory"]) / 1024 / 1024 / 1024)
        odh_dashboard_config.notebook_request_size_cpu = float(k8s_quantity.parse_quantity(notebook_size["resources"]["requests"]["cpu"]))

        odh_dashboard_config.notebook_limit_size_mem = float(k8s_quantity.parse_quantity(notebook_size["resources"]["limits"]["memory"]) / 1024 / 1024 / 1024)
        odh_dashboard_config.notebook_limit_size_cpu = float(k8s_quantity.parse_quantity(notebook_size["resources"]["limits"]["cpu"]))

    return odh_dashboard_config


@ignore_file_not_found
def _parse_pod_times(dirname, hostnames, is_notebook=False):
    if is_notebook:
        filename = pathlib.Path("artifacts-sutest") / "notebook_pods.yaml"
    else:
        filename = pathlib.Path("artifacts-driver") / "tester_pods.yaml"

    pod_times = defaultdict(types.SimpleNamespace)

    in_metadata = False
    in_spec = False
    podname = None
    fmt = f'"{K8S_TIME_FMT}"'

    with open(register_important_file(dirname, filename)) as f:
        for line in f.readlines():
            if line == "  metadata:\n":
                in_metadata = True
                in_status = False
                in_spec = False
                podname = None
                continue

            elif line == "  spec:\n":
                in_metadata = False
                in_spec = True
                in_status = False
                continue

            elif line == "  status:\n":
                in_metadata = False
                in_spec = False
                in_status = True
                continue

            if in_metadata and line.startswith("    name:"):
                _podname = line.strip().split(": ")[1]
                if _podname.endswith("-build"): continue
                if _podname.endswith("-debug"): continue

                if is_notebook:
                    if TEST_USERNAME_PREFIX not in _podname:
                        continue

                    user_idx = int(re.findall(JUPYTER_USER_IDX_REGEX, _podname)[0])
                    _podname = f"{JUPYTER_USER_RENAME_PREFIX}{user_idx}"
                podname = _podname

            if podname is None: continue

            if in_spec and line.startswith("    nodeName:"):
                hostnames[podname] = line.strip().partition(": ")[-1]

            elif in_status and "startTime:" in line:
                pod_times[podname].start_time = \
                    datetime.datetime.strptime(
                        line.strip().partition(": ")[-1],
                        fmt)

            elif in_status and "finishedAt:" in line:
                # this will keep the *last* finish date
                pod_times[podname].container_finished = \
                    datetime.datetime.strptime(
                        line.strip().partition(": ")[-1],
                        fmt)

    return pod_times


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
        return int(f.read())


@ignore_file_not_found
def _parse_ods_ci_output_xml(dirname, output_dir):
    filename = output_dir / "output.xml"

    with open(register_important_file(dirname, filename)) as f:
        output_dict = xmltodict.parse(f.read())

    ods_ci_times = {}
    tests = output_dict["robot"]["suite"]["test"]
    if not isinstance(tests, list): tests = [tests]

    for test in tests:
        if test["status"].get("#text") == 'Failure occurred and exit-on-failure mode is in use.':
            continue

        ods_ci_times[test["@name"]] = test_times = types.SimpleNamespace()

        test_times.start = datetime.datetime.strptime(test["status"]["@starttime"], ROBOT_TIME_FMT)
        test_times.finish = datetime.datetime.strptime(test["status"]["@endtime"], ROBOT_TIME_FMT)
        test_times.status = test["status"]["@status"]

    return ods_ci_times


@ignore_file_not_found
def _parse_ods_ci_notebook_benchmark(dirname, output_dir):
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

    rhods_cluster_info.master = [node_info for node_info in nodes_info.values() \
                                 if node_info.sutest_cluster and node_info.master]

    rhods_cluster_info.infra = [node_info for node_info in nodes_info.values() \
                                if node_info.sutest_cluster and node_info.infra]

    rhods_cluster_info.rhods_compute = [node_info for node_info in nodes_info.values() \
                                  if node_info.sutest_cluster and node_info.rhods_compute]

    rhods_cluster_info.test_pods_only = [node_info for node_info in nodes_info.values() \
                                         if node_info.sutest_cluster and node_info.test_pods_only]

    return rhods_cluster_info


def _parse_always(results, dirname, import_settings):
    # parsed even when reloading from the cache file

    results.from_local_env = _parse_local_env(dirname)
    results.thresholds = store_thresholds.get_thresholds(import_settings)

    results.check_thresholds = import_settings.get("check_thresholds", "no") == "yes"
    if results.check_thresholds:
        logging.info(f"Check thresholds set for {dirname}")

def _parse_directory(fn_add_to_matrix, dirname, import_settings):
    has_cache = False
    try:
        with open(dirname / CACHE_FILENAME, "rb") as f:
            results = pickle.load(f)

        cache_version = getattr(results, "parser_version", None)
        if cache_version != PARSER_VERSION:
            raise ValueError(cache_version)

        has_cache = True
    except ValueError as e:
        cache_version = e.args[0]
        if not cache_version:
            logging.warning("Cache file does not have a version, ignoring.")
        else:
            logging.warning(f"Cache file version '{cache_version}' does not match the parser version '{PARSER_VERSION}', ignoring.")
    except FileNotFoundError:
        pass # Cache file doesn't exit, ignore and parse

    if has_cache:
        _parse_always(results, dirname, import_settings)

        store.add_to_matrix(import_settings, dirname, results, None)

        return


    results = types.SimpleNamespace()

    results.parser_version = PARSER_VERSION
    results.artifacts_version = _parse_artifacts_version(dirname)

    if results.artifacts_version != ARTIFACTS_VERSION:
        if not results.artifacts_version:
            logging.warning("Artifacts does not have a version...")
        else:
            logging.warning("Artifacts version '{results.artifacts_version}' does not match the parser version '{ARTIFACTS_VERSION}' ...")

    _parse_always(results, dirname, import_settings)

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
    results.nodes_info = defaultdict(types.SimpleNamespace)
    results.nodes_info |= _parse_nodes_info(dirname) or {}
    results.nodes_info |= _parse_nodes_info(dirname, sutest_cluster=True) or {}

    results.sutest_ocp_version = _parse_ocp_version(dirname)

    print("_extract_metrics")
    results.metrics = _extract_metrics(dirname)

    results.notebook_pod_userid = notebook_hostnames = {}
    results.testpod_hostnames = testpod_hostnames = {}

    results.notebook_hostnames = notebook_hostnames = {}
    results.testpod_hostnames = testpod_hostnames = {}
    results.pod_times = {}

    print("_parse_pod_times (tester)")
    results.pod_times |= _parse_pod_times(dirname, testpod_hostnames) or {}
    print("_parse_pod_times (notebooks)")
    results.pod_times |= _parse_pod_times(dirname, notebook_hostnames, is_notebook=True) or {}

    results.rhods_cluster_info = _extract_rhods_cluster_info(results.nodes_info)

    results.test_pods = [k for k in results.pod_times.keys() if k.startswith("ods-ci") and not "image" in k]
    results.notebook_pods = [k for k in results.pod_times.keys() if k.startswith(JUPYTER_USER_RENAME_PREFIX)]

    print("_parse_pod_results")
    results.ods_ci_output = {}
    results.ods_ci_exit_code = {}
    results.ods_ci_notebook_benchmark = {}
    results.ods_ci_progress = {}
    for test_pod in results.test_pods:
        ods_ci_dirname = test_pod.rpartition("-")[0]
        output_dir = pathlib.Path("ods-ci") / ods_ci_dirname

        user_id = int(test_pod.split("-")[-2])
        results.ods_ci_output[user_id] = _parse_ods_ci_output_xml(dirname, output_dir)
        results.ods_ci_exit_code[user_id] = _parse_ods_ci_exit_code(dirname, output_dir)
        results.ods_ci_notebook_benchmark[user_id] = _parse_ods_ci_notebook_benchmark(dirname, output_dir)
        results.ods_ci_progress[user_id] = _parse_ods_ci_progress(dirname, output_dir)


    results.possible_machines = store_theoretical.get_possible_machines()

    store.add_to_matrix(import_settings, dirname, results, None)

    with open(dirname / CACHE_FILENAME, "wb") as f:
        pickle.dump(results, f)


def parse_data():
    # delegate the parsing to the simple_store
    store.register_custom_rewrite_settings(_rewrite_settings)
    store_simple.register_custom_parse_results(_parse_directory)

    return store_simple.parse_data()
