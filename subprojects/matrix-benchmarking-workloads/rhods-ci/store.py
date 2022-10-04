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

import matrix_benchmarking.store as store
import matrix_benchmarking.store.simple as store_simple
import matrix_benchmarking.common as common
import matrix_benchmarking.cli_args as cli_args
import matrix_benchmarking.store.prom_db as store_prom_db

import matrix_benchmarking.cli_args as cli_args

from . import k8s_quantity
from . import store_theoretical
from .plotting import prom as rhods_plotting_prom

K8S_EVT_TIME_FMT = "%Y-%m-%dT%H:%M:%S.%fZ"
K8S_TIME_FMT = "%Y-%m-%dT%H:%M:%SZ"
ROBOT_TIME_FMT = "%Y%m%d %H:%M:%S.%f"
SHELL_DATE_TIME_FMT = "%a %b %d %H:%M:%S %Z %Y"

JUPYTER_USER_RENAME_PREFIX = "jupyterhub-nb-user"

TEST_USERNAME_PREFIX = "psapuser"
JUPYTER_USER_IDX_REGEX = r'[:letter:]*(\d+)-0$'

def _rewrite_settings(settings_dict):
    return settings_dict


def _parse_env(filename):
    from_env = types.SimpleNamespace()

    if not cli_args.kwargs.get("generate"):
        # running in interactive mode

        from_env.link_flag = "interactive"
    else:
        # running in generate mode

        # This must be parsed from the process env (not the file), to
        # properly generate the error report links to the image.
        job_name = os.getenv("JOB_NAME_SAFE")

        if not job_name:
            # not running in the CI

            from_env.link_flag = "running-locally"
        elif job_name.startswith("nb-ux-on-") or job_name == "get-cluster":
            # running right after the test

            from_env.link_flag = "running-with-the-test"
        elif job_name.startswith("plot-nb-ux-on-"):
            # running independently of the test

            from_env.link_flag = "running-without-the-test"
        else:
            raise ValueError(f"Unexpected value for 'JOB_NAME_SAFE' env var: '{job_name}'")

    from_env.env = {}
    from_env.pr = None
    with open(filename) as f:
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


def _parse_pr(pr_file):
    try:
        with open(pr_file) as f:
            return json.load(f)
    except FileNotFoundError:
        return None


def _parse_pr_comments(pr_comments_file):
    try:
        with open(pr_comments_file) as f:
            return json.load(f)
    except FileNotFoundError:
        return None


def _parse_rhods_info(dirname):
    rhods_info = types.SimpleNamespace()

    try:
        with open(dirname / "artifacts-sutest" / "rhods.version") as f:
            rhods_info.version = f.read().strip()
    except FileNotFoundError:
        rhods_info.version = "not available"

    return rhods_info


def _parse_tester_job(filename):
    job_info = types.SimpleNamespace()

    with open(filename) as f:
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


def _parse_nodes_info(filename, sutest_cluster=False):
    nodes_info = {}
    with open(filename) as f:
        nodeList = yaml.safe_load(f)

    for node in nodeList["items"]:
        node_name = node["metadata"]["name"]
        node_info = nodes_info[node_name] = types.SimpleNamespace()

        node_info.name = node_name
        node_info.sutest_cluster = sutest_cluster
        node_info.managed = "managed.openshift.com/customlabels" in node["metadata"]["annotations"]
        node_info.instance_type = node["metadata"]["labels"]["node.kubernetes.io/instance-type"]

        node_info.master = "node-role.kubernetes.io/master" in node["metadata"]["labels"]
        node_info.notebooks_only = node["metadata"]["labels"].get("only-rhods-notebooks") == "yes"
        node_info.test_pods_only = node["metadata"]["labels"].get("only-test-pods") == "yes"
        node_info.infra = \
            not node_info.master and \
            not node_info.notebooks_only and \
            not node_info.test_pods_only

    return nodes_info


def _parse_odh_dashboard_config(base_dirname, filename, notebook_size_name):
    odh_dashboard_config = types.SimpleNamespace()

    odh_dashboard_config.path = None
    if not filename.exists():
        return odh_dashboard_config

    odh_dashboard_config.path = str(filename.relative_to(base_dirname.parent))

    with open(filename) as f:
        odh_dashboard_config.content = yaml.safe_load(f)

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


def _parse_pod_times(metrics, hostnames, is_notebook=False):
    pod_times = defaultdict(types.SimpleNamespace)

    for metric in metrics:
        if "node" not in metric["metric"]: continue

        podname = metric["metric"]["pod"]
        if podname.endswith("-build"): continue
        if podname.endswith("-debug"): continue

        if is_notebook:
            if TEST_USERNAME_PREFIX not in podname: continue

            user_idx = int(re.findall(JUPYTER_USER_IDX_REGEX, podname)[0])
            podname = f"{JUPYTER_USER_RENAME_PREFIX}{user_idx}"

        pod_times[podname] = types.SimpleNamespace()

        pod_times[podname].start_time = datetime.datetime.fromtimestamp(metric["values"][0][0])

        pod_times[podname].container_finished = datetime.datetime.fromtimestamp(metric["values"][-1][0])

        if hostnames is not None:
            hostnames[podname] = metric["metric"]["node"]

    return pod_times

def _parse_ods_ci_exit_code(filename):
    if not filename.exists():
        logging.error(f"_parse_ods_ci_exit_code: '{filename}' doesn't exist ...")
        return

    with open(filename) as f:
        return int(f.read())

def _parse_ods_ci_output_xml(filename):
    ods_ci_times = {}

    if not filename.exists():
        logging.error(f"_parse_ods_ci_output_xml: '{filename}' doesn't exist ...")
        return {}

    with open(filename) as f:
        output_dict = xmltodict.parse(f.read())

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

        results_metrics[name] = store_prom_db.extract_metrics(prom_tarball, metrics, dirname)

    return results_metrics


def _parse_ods_ci_notebook_benchmark(fname):
    try:
        with open(fname) as f:
            return json.load(f)
    except FileNotFoundError:
        return None


def _parse_ods_ci_progress(fname):
    try:
        with open(fname) as f:
            progress = yaml.safe_load(f)
    except FileNotFoundError:
        return {}

    for key, date_str in progress.items():
        progress[key] = datetime.datetime.strptime(date_str, SHELL_DATE_TIME_FMT)

    return progress

def _extract_rhods_cluster_info(nodes_info):
    rhods_cluster_info = types.SimpleNamespace()

    rhods_cluster_info.node_count = [node_info for node_info in nodes_info.values() \
                                     if node_info.sutest_cluster]

    rhods_cluster_info.master = [node_info for node_info in nodes_info.values() \
                                  if node_info.sutest_cluster and node_info.master]

    rhods_cluster_info.infra = [node_info for node_info in nodes_info.values() \
                                  if node_info.sutest_cluster and node_info.infra]

    rhods_cluster_info.notebooks_only = [node_info for node_info in nodes_info.values() \
                                         if node_info.sutest_cluster and node_info.notebooks_only]

    rhods_cluster_info.test_pods_only = [node_info for node_info in nodes_info.values() \
                                         if node_info.sutest_cluster and node_info.test_pods_only]

    return rhods_cluster_info


def _parse_directory(fn_add_to_matrix, dirname, import_settings):
    results = types.SimpleNamespace()

    results.user_count = int(import_settings["user_count"])
    results.location = dirname
    results.source_url = None
    if os.getenv("JOB_NAME_SAFE", "").startswith("plot-nb-ux-on-"):
        with open(pathlib.Path(os.getenv("ARTIFACT_DIR")) / "source_url") as f:
            results.source_url = f.read().strip()

    results.tester_job = _parse_tester_job(dirname / "artifacts-driver" / "tester_job.yaml")
    results.from_env = _parse_env(dirname / "_ansible.env")

    results.from_pr = _parse_pr(dirname.parent / "pull_request.json")
    results.pr_comments = _parse_pr_comments(dirname.parent / "pull_request-comments.json",)

    results.rhods_info = _parse_rhods_info(dirname)

    print("_parse_odh_dashboard_config")
    notebook_size_name = results.tester_job.env.get("NOTEBOOK_SIZE_NAME")
    results.odh_dashboard_config = _parse_odh_dashboard_config(dirname, dirname / "artifacts-sutest" / "odh-dashboard-config.yaml", notebook_size_name)

    print("_parse_nodes_info")
    results.nodes_info = defaultdict(types.SimpleNamespace)
    results.nodes_info |= _parse_nodes_info(dirname / "artifacts-driver" / "nodes.yaml")
    results.nodes_info |= _parse_nodes_info(dirname / "artifacts-sutest" / "nodes.yaml", sutest_cluster=True)

    with open(dirname / "artifacts-sutest" / "ocp_version.yml") as f:
        ocp_version_yaml = yaml.safe_load(f)
        results.sutest_ocp_version = ocp_version_yaml["openshiftVersion"]

    print("_extract_metrics")
    results.metrics = _extract_metrics(dirname)

    results.notebook_pod_userid = notebook_hostnames = {}
    results.testpod_hostnames = testpod_hostnames = {}

    results.notebook_hostnames = notebook_hostnames = {}
    results.testpod_hostnames = testpod_hostnames = {}
    print("_parse_pod_times (tester)")
    results.pod_times = {}


    print("_parse_pod_times (notebooks)")

    results.pod_times |= _parse_pod_times(
        results.metrics["sutest"]["sutest__container_cpu_requests__namespace=rhods-notebooks_container=jupyter-nb-psapuser.*"],
        notebook_hostnames, is_notebook=True)
    results.pod_times |= _parse_pod_times(
        results.metrics["driver"]["driver__container_cpu_requests__namespace=loadtest_container=main"],
        testpod_hostnames)
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
        output_dir = dirname / "ods-ci" / ods_ci_dirname

        user_id = int(test_pod.split("-")[-2])
        results.ods_ci_output[user_id] = _parse_ods_ci_output_xml(output_dir / "output.xml")
        results.ods_ci_exit_code[user_id] = _parse_ods_ci_exit_code(output_dir / "test.exit_code")
        results.ods_ci_notebook_benchmark[user_id] = _parse_ods_ci_notebook_benchmark(output_dir / "benchmark_measures.json")
        results.ods_ci_progress[user_id] = _parse_ods_ci_progress(output_dir / "progress_ts.yaml")

    results.user_count = int(import_settings["user_count"])

    results.possible_machines = store_theoretical.get_possible_machines()

    store.add_to_matrix(import_settings, None, results, None)

def parse_data():
    # delegate the parsing to the simple_store
    store.register_custom_rewrite_settings(_rewrite_settings)
    store_simple.register_custom_parse_results(_parse_directory)

    return store_simple.parse_data()
