import types
import pathlib
import logging
import yaml
import os
import json
import datetime
from collections import defaultdict

import jsonpath_ng

import matrix_benchmarking.cli_args as cli_args
import matrix_benchmarking.store.prom_db as store_prom_db

from . import prom as rhods_pipelines_prom


register_important_file = None # will be when importing store/__init__.py

K8S_TIME_FMT = "%Y-%m-%dT%H:%M:%SZ"
SHELL_DATE_TIME_FMT = "%a %b %d %H:%M:%S %Z %Y"
ANSIBLE_LOG_DATE_TIME_FMT = "%Y-%m-%d %H:%M:%S"

IMPORTANT_FILES = [
    "artifacts_version",
    "config.yaml",
    "000__local_ci__run_multi/success_count",
    "000__local_ci__run_multi/ci_job.yaml",
    "000__local_ci__run_multi/prometheus_ocp.t*",

    "000__local_ci__run_multi/artifacts/ci-pod-*/progress_ts.yaml",
    "000__local_ci__run_multi/artifacts/ci-pod-*/test.exit_code",
    "000__local_ci__run_multi/artifacts/ci-pod-*/*/_ansible.log",
    "000__local_ci__run_multi/artifacts/ci-pod-*/004__pipelines__capture_state/pods/*.json",

    "000__local_ci__run_multi/artifacts/ci-pod-*/applications.json",
    "000__local_ci__run_multi/artifacts/ci-pod-*/deployments.json",
    "000__local_ci__run_multi/artifacts/ci-pod-*/pipelines.json",

    "001__notebooks__capture_state/nodes.json",
    "001__notebooks__capture_state/ocp_version.yml",
    "001__notebooks__capture_state/rhods.version",
    "001__notebooks__capture_state/rhods.createdAt",
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


def _parse_always(results, dirname, import_settings):
    # parsed even when reloading from the cache file

    results.from_local_env = _parse_local_env(dirname)
    results.test_config = _parse_test_config(dirname)

def _parse_once(results, dirname):
    results.artifacts_version = _parse_artifacts_version(dirname)
    if results.artifacts_version != ARTIFACTS_VERSION:
        if not results.artifacts_version:
            logging.warning("Artifacts does not have a version...")
        else:
            logging.warning(f"Artifacts version '{results.artifacts_version}' does not match the parser version '{ARTIFACTS_VERSION}' ...")

    results.user_count = int(results.test_config.get("tests.pipelines.user_count"))
    results.nodes_info = _parse_nodes_info(dirname) or {}
    results.rhods_cluster_info = _extract_rhods_cluster_info(results.nodes_info)
    results.sutest_ocp_version = _parse_ocp_version(dirname)
    results.rhods_info = _parse_rhods_info(dirname)
    results.success_count = _parse_success_count(dirname)
    results.user_data = _parse_user_data(dirname, results.user_count)
    results.tester_job = _parse_tester_job(dirname)
    results.metrics = _extract_metrics(dirname)


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

@ignore_file_not_found
def _parse_nodes_info(dirname, sutest_cluster=True):
    nodes_info = {}

    filename = "001__notebooks__capture_state/nodes.json"

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
def _parse_ocp_version(dirname):
    filename = "001__notebooks__capture_state/ocp_version.yml"

    with open(register_important_file(dirname, filename)) as f:
        sutest_ocp_version_yaml = yaml.safe_load(f)

    return sutest_ocp_version_yaml["openshiftVersion"]

@ignore_file_not_found
def _parse_rhods_info(dirname):
    rhods_info = types.SimpleNamespace()
    artifact_dirname = pathlib.Path("001__notebooks__capture_state")

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
            ts = datetime.datetime.strptime(ts_str, ANSIBLE_LOG_DATE_TIME_FMT)
            ansible_progress[f"ansible.{step_name}"] = ts

    return ansible_progress

def _parse_user_data(dirname, user_count):
    user_data = {}
    for user_id in range(user_count):
        ci_pod_dirname = dirname / "000__local_ci__run_multi" / "artifacts" / f"ci-pod-{user_id}"
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

    return user_data

@ignore_file_not_found
def _parse_tester_job(dirname):
    job_info = types.SimpleNamespace()

    with open(register_important_file(dirname, "000__local_ci__run_multi/ci_job.yaml")) as f:
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

    return job_info

def _extract_metrics(dirname):
    METRICS = {
        "sutest": ("000__local_ci__run_multi/prometheus_ocp.t*", rhods_pipelines_prom.get_sutest_metrics()),
        "driver": ("000__local_ci__run_multi/prometheus_ocp.t*", rhods_pipelines_prom.get_driver_metrics()),
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

@ignore_file_not_found
def _parse_artifacts_version(dirname):
    with open(dirname / "artifacts_version") as f:
        artifacts_version = f.read().strip()

    return artifacts_version


@ignore_file_not_found
def _parse_pod_times(dirname, ci_pod_dir):
    filenames = [fname.relative_to(dirname) for fname in
                 ci_pod_dir.glob("00*__pipelines__capture_state/pods/*.json")]

    pod_times = []

    def _parse_pod_times_file(filename, pod):
        pod_time = types.SimpleNamespace()
        pod_times.append(pod_time)

        if pod["metadata"]["labels"].get("component") == "data-science-pipelines":
            pod_friendly_name = pod["metadata"]["labels"]["app"]
            pod_time.is_dspa = True

        elif pod["metadata"]["labels"].get("app.kubernetes.io/managed-by") == "tekton-pipelines":
            pod_friendly_name = pod["metadata"]["labels"]["tekton.dev/pipelineTask"]
            pod_time.is_pipeline_task = True

        elif pod["metadata"].get("generateName"):
            pod_friendly_name = pod["metadata"]["generateName"]\
                .replace("-"+pod["metadata"]["labels"].get("pod-template-hash", "")+"-", "")\
                .strip("-")

            if pod_friendly_name == "minio-deployment":
                pod_time.is_dspa = True
        else:
            pod_name = pod["metadata"]["name"]

        pod_time.pod_name = pod["metadata"]["name"]
        pod_time.pod_friendly_name = pod_friendly_name
        pod_time.pod_namespace = pod["metadata"]["namespace"]
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
            except KeyError: continue

            # take the last container_finished found
            if ("container_finished" not in pod_time.__dict__
                or pod_time.container_finished < finishedAt):
                pod_time.container_finished = finishedAt

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

    @ignore_file_not_found
    def parse(fname):
        print(f"Parsing {fname} ...")
        file_path = (ci_pod_dir / "004__pipelines__capture_state" / fname).resolve().relative_to(dirname)

        with open(register_important_file(dirname, file_path)) as f:
            data = yaml.safe_load(f)

        for item in data["items"]:
            metadata = item["metadata"]

            kind = item["kind"]
            creationTimestamp = datetime.datetime.strptime(
                metadata["creationTimestamp"], K8S_TIME_FMT)

            name = metadata["name"]
            generate_name, found, suffix = name.rpartition("-")
            remove_suffix = ((found and not suffix.isalpha()))

            if remove_suffix:
                name = generate_name # remove generated suffix

            all_resource_times[f"{kind}/{name}"] = creationTimestamp

    parse("applications.json")
    parse("deployments.json")
    parse("pipelines.json")

    return dict(all_resource_times)
