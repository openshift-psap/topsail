import types
import pathlib
import logging
import yaml
import os
import json
import datetime

import jsonpath_ng

import matrix_benchmarking.cli_args as cli_args
import matrix_benchmarking.store.prom_db as store_prom_db

from . import prom as workload_prom


register_important_file = None # will be when importing store/__init__.py

K8S_TIME_FMT = "%Y-%m-%dT%H:%M:%SZ"
SHELL_DATE_TIME_FMT = "%a %b %d %H:%M:%S %Z %Y"
ANSIBLE_LOG_DATE_TIME_FMT = "%Y-%m-%d %H:%M:%S"

artifact_dirnames = types.SimpleNamespace()
artifact_dirnames.CLUSTER_CAPTURE_ENV_DIR = "*__cluster__capture_environment"
artifact_dirnames.LOCAL_CI_RUN_MULTI_DIR = "*__local_ci__run_multi"
artifact_dirnames.WATSONX_SERVING_CAPTURE_OPERATORS_STATE_DIR = "*__watsonx_serving__capture_operators_state"

artifact_paths = None # store._parse_directory will turn it into a {str: pathlib.Path} dict base on ^^^

IMPORTANT_FILES = [
    "config.yaml",

    f"{artifact_dirnames.LOCAL_CI_RUN_MULTI_DIR}/ci_job.yaml",
    f"{artifact_dirnames.LOCAL_CI_RUN_MULTI_DIR}/prometheus_ocp.t*",
    f"{artifact_dirnames.LOCAL_CI_RUN_MULTI_DIR}/success_count",
    f"{artifact_dirnames.LOCAL_CI_RUN_MULTI_DIR}/ci-pods_artifacts/ci-pod-*/progress_ts.yaml",
    f"{artifact_dirnames.LOCAL_CI_RUN_MULTI_DIR}/ci-pods_artifacts/ci-pod-*/test.exit_code",
    f"{artifact_dirnames.CLUSTER_CAPTURE_ENV_DIR}/nodes.json",
    f"{artifact_dirnames.CLUSTER_CAPTURE_ENV_DIR}/ocp_version.yml",
    f"{artifact_dirnames.WATSONX_SERVING_CAPTURE_OPERATORS_STATE_DIR}/rhods.createdAt",
    f"{artifact_dirnames.WATSONX_SERVING_CAPTURE_OPERATORS_STATE_DIR}/rhods.version",
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


def _parse_once(results, dirname):
    results.user_count = int(results.test_config.get("tests.scale.namespace_count"))

    results.nodes_info = _parse_nodes_info(dirname) or {}
    results.cluster_info = _extract_cluster_info(results.nodes_info)
    results.sutest_ocp_version = _parse_ocp_version(dirname)
    results.metrics = _extract_metrics(dirname)
    results.test_start_end_time = _parse_start_end_time(dirname)
    results.user_data = _parse_user_data(dirname, results.user_count)
    results.success_count = _parse_success_count(dirname)
    results.file_locations = _parse_file_locations(dirname)
    results.rhods_info = _parse_rhods_info(dirname)

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

    filename = artifact_paths.CLUSTER_CAPTURE_ENV_DIR / "nodes.json"

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

    with open(register_important_file(dirname, artifact_paths.CLUSTER_CAPTURE_ENV_DIR / "ocp_version.yml")) as f:
        sutest_ocp_version_yaml = yaml.safe_load(f)

    return sutest_ocp_version_yaml["openshiftVersion"]


@ignore_file_not_found
def _parse_rhods_info(dirname):
    rhods_info = types.SimpleNamespace()
    artifact_dirname = pathlib.Path("001__rhods__capture_state")

    with open(register_important_file(dirname, artifact_paths.WATSONX_SERVING_CAPTURE_OPERATORS_STATE_DIR / "rhods.version")) as f:
        rhods_info.version = f.read().strip()

    with open(register_important_file(dirname, artifact_paths.WATSONX_SERVING_CAPTURE_OPERATORS_STATE_DIR / "rhods.createdAt")) as f:
        rhods_info.createdAt_raw = f.read().strip()

    try:
        rhods_info.createdAt = datetime.datetime.strptime(rhods_info.createdAt_raw, K8S_TIME_FMT)
    except ValueError as e:
        import pdb;pdb.set_trace()
        logging.error(f"Couldn't parse RHODS version timestamp: {e}")
        rhods_info.createdAt = None

    rhods_info.full_version = (
        f"{rhods_info.version}-" \
        + (rhods_info.createdAt.strftime("%Y-%m-%d")
           if rhods_info.createdAt else "0000-00-00"))

    return rhods_info

def _extract_metrics(dirname):
    METRICS = {
        "sutest": (str(artifact_paths.LOCAL_CI_RUN_MULTI_DIR / "prometheus_ocp.t*"), workload_prom.get_sutest_metrics()),
    }

    metrics = {}
    for name, (tarball_glob, metric) in METRICS.items():
        try:
            prom_tarball = list(dirname.glob(tarball_glob))[0]
        except IndexError:
            logging.warning(f"No {tarball_glob} in '{dirname}'.")
            continue

        register_important_file(dirname, prom_tarball.relative_to(dirname))
        metrics[name] = store_prom_db.extract_metrics(prom_tarball, metric, dirname)

    return metrics

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


@ignore_file_not_found
def _parse_success_count(dirname):
    filename = pathlib.Path("000__local_ci__run_multi") / "success_count"

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
        progress[f"progress_ts.{idx:03d}__{key}"] = datetime.datetime.strptime(date_str, SHELL_DATE_TIME_FMT)

    return progress


def _parse_user_data(dirname, user_count):
    user_data = {}
    for user_id in range(user_count):
        ci_pod_dirname = artifact_paths.LOCAL_CI_RUN_MULTI_DIR / "ci-pods_artifacts" / f"ci-pod-{user_id}"
        ci_pod_dirpath = dirname / ci_pod_dirname
        if not (dirname / ci_pod_dirname).exists():
            user_data[user_id] = None
            logging.warning(f"No user directory collected for user #{user_id} ({ci_pod_dirname})")
            continue

        user_data[user_id] = data = types.SimpleNamespace()
        data.artifact_dir = ci_pod_dirname
        data.exit_code = _parse_user_exit_code(dirname, ci_pod_dirpath)
        data.progress = _parse_user_progress(dirname, ci_pod_dirpath)

    return user_data


def _parse_file_locations(dirname):
    file_locations = types.SimpleNamespace()

    file_locations.test_config_file = pathlib.Path("config.yaml")
    register_important_file(dirname, file_locations.test_config_file)

    return file_locations
