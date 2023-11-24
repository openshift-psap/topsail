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
artifact_dirnames.CLUSTER_DUMP_PROM_DB_DIR = "*__cluster__dump_prometheus_db"
artifact_dirnames.CLUSTER_CAPTURE_ENV_DIR = "*__cluster__capture_environment"
artifact_dirnames.LOAD_AWARE_SCALE_TEST_DIR = "*__load_aware__scale_test"

artifact_paths = None # store._parse_directory will turn it into a {str: pathlib.Path} dict base on ^^^

IMPORTANT_FILES = [
    "config.yaml",
    f"{artifact_dirnames.LOAD_AWARE_SCALE_TEST_DIR}/trimaran_scheduler.log",
    f"{artifact_dirnames.LOAD_AWARE_SCALE_TEST_DIR}/scale_test_pods.json",
    f"{artifact_dirnames.CLUSTER_CAPTURE_ENV_DIR}/nodes.json",
    f"{artifact_dirnames.CLUSTER_CAPTURE_ENV_DIR}/ocp_version.yml",
    f"{artifact_dirnames.CLUSTER_DUMP_PROM_DB_DIR}/prometheus.t*"
]

PARSER_VERSION = "2023-07-07"
ARTIFACTS_VERSION = "2023-07-07"

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
    results.pods_info = _parse_pod_times(dirname) or {}
    results.nodes_info = _parse_nodes_info(dirname) or {}
    results.cluster_info = _extract_cluster_info(results.nodes_info)
    results.sutest_ocp_version = _parse_ocp_version(dirname)
    results.metrics = _extract_metrics(dirname)
    results.file_locations = _parse_file_locations(dirname)

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
def _parse_pod_times(dirname):

    filename = artifact_paths.LOAD_AWARE_SCALE_TEST_DIR / "scale_test_pods.json"

    with open(register_important_file(dirname, filename)) as f:
        try:
            json_file = json.load(f)
        except Exception as e:
            logging.error(f"Couldn't parse JSON file '{filename}': {e}")
            return

    pod_times = []
    for pod in json_file["items"]:
        pod_time = types.SimpleNamespace()
        pod_times.append(pod_time)

        pod_time.pod_name = pod["metadata"]["name"]
        pod_time.workload = pod["metadata"]["labels"]["workload"]

        pod_time.hostname = pod["spec"].get("nodeName")

        pod_time.creation_time = datetime.datetime.strptime(
                pod["metadata"]["creationTimestamp"], K8S_TIME_FMT)

        start_time_str = pod["status"].get("startTime")
        pod_time.start_time = None if not start_time_str else \
            datetime.datetime.strptime(start_time_str, K8S_TIME_FMT)

        for condition in pod["status"].get("conditions", []):
            last_transition = datetime.datetime.strptime(condition["lastTransitionTime"], K8S_TIME_FMT)

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
                    K8S_TIME_FMT)
                startedAt = datetime.datetime.strptime(
                        containerStatus["state"]["terminated"]["startedAt"],
                        K8S_TIME_FMT)
            except KeyError: continue

            # take the last container_finished found
            if ("container_finished" not in pod_time.__dict__
                or pod_time.container_finished < finishedAt):
                pod_time.container_finished = finishedAt

          # take the last container_finished found
            if ("container_started" not in pod_time.__dict__
                or pod_time.container_started < startedAt):
                pod_time.container_started = startedAt

    return pod_times

@ignore_file_not_found
def _parse_nodes_info(dirname, sutest_cluster=True):
    nodes_info = {}

    if not artifact_paths.CLUSTER_CAPTURE_ENV_DIR:
        raise FileNotFoundError(artifact_dirnames.CLUSTER_CAPTURE_ENV_DIR)

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

        node_info.infra = not node_info.control_plane

        node_info.workload = node["metadata"]["labels"].get("only-workload-pods")

    return nodes_info


@ignore_file_not_found
def _parse_ocp_version(dirname):

    filename = artifact_paths.CLUSTER_CAPTURE_ENV_DIR / "ocp_version.yml"

    with open(register_important_file(dirname, filename)) as f:
        sutest_ocp_version_yaml = yaml.safe_load(f)

    return sutest_ocp_version_yaml["openshiftVersion"]

def _parse_file_locations(dirname):
    file_locations = types.SimpleNamespace()

    file_locations.trimaran_log = artifact_paths.LOAD_AWARE_SCALE_TEST_DIR / "trimaran_scheduler.log"
    register_important_file(dirname, file_locations.trimaran_log)

    file_locations.test_config_file = pathlib.Path("config.yaml")
    register_important_file(dirname, file_locations.test_config_file)

    return file_locations

@ignore_file_not_found
def _extract_metrics(dirname):

    if not artifact_paths.CLUSTER_DUMP_PROM_DB_DIR:
        raise FileNotFoundError(artifact_dirnames.CLUSTER_DUMP_PROM_DB_DIR)

    METRICS = {
        "sutest": (str(artifact_paths.CLUSTER_DUMP_PROM_DB_DIR / "prometheus.t*"), workload_prom.get_sutest_metrics()),
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

    cluster_info.workload = [node_info for node_info in nodes_info.values() \
                             if node_info.sutest_cluster and node_info.workload]

    return cluster_info
