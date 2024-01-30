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
from . import lts_parser

register_important_file = None # will be when importing store/__init__.py

K8S_TIME_FMT = "%Y-%m-%dT%H:%M:%SZ"
SHELL_DATE_TIME_FMT = "%a %b %d %H:%M:%S %Z %Y"
ANSIBLE_LOG_DATE_TIME_FMT = "%Y-%m-%d %H:%M:%S"

IMPORTANT_FILES = [
    "config.yaml",
    "_ansible.log",
    "_ansible.env",
    ".uuid",

    "artifacts-sutest/nodes.json",
    "artifacts-sutest/ocp_version.yml",
    "artifacts-sutest/rhods.version",
    "artifacts-sutest/rhods.createdAt",

    "notebook-artifacts/benchmark_measures.json",
]

PARSER_VERSION = "2023-05-31"
ARTIFACTS_VERSION = "2023-05-31"

def ignore_file_not_found(fn):
    def decorator(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except FileNotFoundError as e:
            logging.warning(f"{fn.__name__}: FileNotFoundError: {e}")
            return None

    return decorator


def _parse_always(results, dirname, import_settings):
    # parsed even when reloading from the cache file

    results.from_local_env = _parse_local_env(dirname)
    results.test_config = _parse_test_config(dirname)
    results.regression_results = _parse_regression_results(dirname)
    results.lts = lts_parser.generate_lts_payload(results, import_settings, must_validate=False)


def _parse_once(results, dirname):
    results.nodes_info = _parse_nodes_info(dirname) or {}
    results.cluster_info = _extract_cluster_info(results.nodes_info)
    results.sutest_ocp_version = _parse_ocp_version(dirname)
    results.rhods_info = _parse_rhods_info(dirname)
    results.start_time, results.end_time = _parse_start_end_time(dirname)
    results.notebook_benchmark = _parse_notebook_benchmark(dirname, pathlib.Path("notebook-artifacts"))
    results.test_uuid = _parse_test_uuid(dirname)
    results.from_env = _parse_env(dirname)


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
    job_name = os.getenv("JOB_NAME_SAFE", "")

    if job_name.endswith("-plot"):
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
        logging.error(f"Unknown execution environment: JOB_NAME_SAFE={job_name} ARTIFACT_DIR={os.environ.get('ARTIFACT_DIR')}")
        from_local_env.artifacts_basedir = dirname.absolute()

    return from_local_env


@ignore_file_not_found
def _parse_test_uuid(dirname):
    with open(dirname / ".uuid") as f:
        test_uuid = f.read().strip()

    return uuid.UUID(test_uuid)


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


@ignore_file_not_found
def _parse_nodes_info(dirname, sutest_cluster=True):
    nodes_info = {}

    filename = pathlib.Path("artifacts-sutest") / "nodes.json"

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

        node_info.infra = \
            not node_info.control_plane

    return nodes_info


@ignore_file_not_found
def _parse_ocp_version(dirname):

    with open(register_important_file(dirname, pathlib.Path("artifacts-sutest") / "ocp_version.yml")) as f:
        sutest_ocp_version_yaml = yaml.safe_load(f)

    return sutest_ocp_version_yaml["openshiftVersion"]


@ignore_file_not_found
def _extract_cluster_info(nodes_info):
    cluster_info = types.SimpleNamespace()

    cluster_info.node_count = [node_info for node_info in nodes_info.values() \
                                     if node_info.sutest_cluster]

    cluster_info.control_plane = [node_info for node_info in nodes_info.values() \
                                 if node_info.sutest_cluster and node_info.control_plane]

    cluster_info.infra = [node_info for node_info in nodes_info.values() \
                                if node_info.sutest_cluster and node_info.infra]

    return cluster_info


@ignore_file_not_found
def _parse_rhods_info(dirname):
    rhods_info = types.SimpleNamespace()
    artifact_dirname = pathlib.Path("artifacts-sutest")

    with open(register_important_file(dirname, artifact_dirname / "rhods.version")) as f:
        rhods_info.version = f.read().strip()

    with open(register_important_file(dirname, artifact_dirname / "rhods.createdAt")) as f:
        rhods_info.createdAt_raw = f.read().strip()

    try:
        rhods_info.createdAt = datetime.datetime.strptime(rhods_info.createdAt_raw, K8S_TIME_FMT)
    except ValueError as e:
        logging.error("Couldn't parse RHODS version timestamp: {e}")
        rhods_info.createdAt = None

    rhods_info.full_version = (
        f"{rhods_info.version}-" \
        + (rhods_info.createdAt.strftime("%Y-%m-%d")
           if rhods_info.createdAt else "0000-00-00"))

    return rhods_info


@ignore_file_not_found
def _parse_notebook_benchmark(dirname, output_dir):
    filename = output_dir / "benchmark_measures.json"
    with open(register_important_file(dirname, filename)) as f:
        return json.load(f)

@ignore_file_not_found
def _parse_start_end_time(dirname):
    ANSIBLE_LOG_TIME_FMT = '%Y-%m-%d %H:%M:%S'
    start_time = None
    end_time = None
    with open(register_important_file(dirname, "_ansible.log")) as f:
        for line in f.readlines():
            time_str = line.partition(",")[0] # ignore the MS
            if start_time is None:
                start_time = datetime.datetime.strptime(time_str, ANSIBLE_LOG_TIME_FMT)
        if start_time is None:
            raise ValueError("Ansible log file is empty :/")

        end_time = datetime.datetime.strptime(time_str, ANSIBLE_LOG_TIME_FMT)

    return start_time, end_time


def _parse_regression_results(dirname):
    regression_results_file = dirname / "regression.json"
    if not regression_results_file.exists():
        logging.info(f"{regression_results_file.name} does not exist, ignoring the parsing of the regression analyses results.")
        return None

    with open(regression_results_file) as f:
        regression_results = json.load(f)

    return regression_results


@ignore_file_not_found
def _parse_env(dirname):
    from_env = types.SimpleNamespace()

    ansible_env = {}

    from_env.test = types.SimpleNamespace()
    from_env.test.run_id = None
    from_env.test.test_path = None
    from_env.test.ci_engine = None
    from_env.test.urls = {}

    with open(register_important_file(dirname, "_ansible.env")) as f:
        for line in f.readlines():
            k, _, v = line.strip().partition("=")

            ansible_env[k] = v

    if ansible_env.get("OPENSHIFT_CI") == "true":
        from_env.test.ci_engine = "OPENSHIFT_CI"
        job_spec = json.loads(ansible_env["JOB_SPEC"])
        entrypoint_options = json.loads(ansible_env["ENTRYPOINT_OPTIONS"])

        #

        pull_number = job_spec["refs"]["pulls"][0]["number"]
        github_org = job_spec["refs"]["org"]
        github_repo = job_spec["refs"]["repo"]

        job = job_spec["job"]
        build_id = job_spec["buildid"]

        test_name = ansible_env.get("JOB_NAME_SAFE")
        step_name = entrypoint_options["container_name"]

        # ---
        # eg: pull/openshift-psap_topsail/181/pull-ci-openshift-psap-topsail-main-rhoai-light/1749833488137195520

        from_env.test.run_id = f"pull/{github_org}_{github_repo}/{pull_number}/{job}/{build_id}"

        # ---
        # eg 003__notebook_performance/003__sutest_notebooks__benchmark_performance/
        current_artifact_dir = pathlib.Path(ansible_env["ARTIFACT_DIR"])
        base_artifact_dir = entrypoint_options["artifact_dir"]

        if dirname.name == "from_url":
            with open(dirname / "source_url") as f: # not an important file
                source_url = f.read().strip()
            _prefix, _, from_env.test.test_path = source_url.partition(f"{from_env.test.run_id}/artifacts/")
        else:
            from_env.test.test_path = str(f"{test_name}/{step_name}/artifacts" / (current_artifact_dir / dirname).relative_to(base_artifact_dir))

        # ---
        from_env.test.urls |= dict(
            PROW_JOB=f"https://prow.ci.openshift.org/view/gs/test-platform-results/pr-logs/{from_env.test.run_id}",
            PROW_ARTIFACTS=f"https://gcsweb-ci.apps.ci.l2s4.p1.openshiftapps.com/gcs/test-platform-results/pr-logs/{from_env.test.run_id}/artifacts/{from_env.test.test_path}"
        )

    if ansible_env.get("PERFLAB_CI") == "true":
        from_env.test.ci_engine = "OPENSHIFT_CI"
        from_env.test.test_path = "test/path/not/available"
        from_env.test.run_id = "run/id/not/available"

        from_env.test.urls |= dict(
            JENKINS_ARTIFACTS=f"NOT AVAILABLE YET"
        )

    return from_env
