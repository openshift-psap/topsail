import types
import pathlib
import logging
import yaml
import os
import json
import datetime
import dateutil.parser
import uuid

import jsonpath_ng

import matrix_benchmarking.cli_args as cli_args
import matrix_benchmarking.store.prom_db as store_prom_db

from . import prom as workload_prom

register_important_file = None # will be when importing store/__init__.py

K8S_TIME_FMT = "%Y-%m-%dT%H:%M:%SZ"
SHELL_DATE_TIME_FMT = "%a %b %d %H:%M:%S %Z %Y"
ANSIBLE_LOG_DATE_TIME_FMT = "%Y-%m-%d %H:%M:%S"

artifact_dirnames = types.SimpleNamespace()
artifact_dirnames.CLUSTER_DUMP_PROM_DB_DIR = "*__cluster__dump_prometheus_dbs/*__cluster__dump_prometheus_db"
artifact_dirnames.CLUSTER_DUMP_PROM_DB_UWM_DIR = "*__cluster__dump_prometheus_dbs/*__cluster__dump_prometheus_db_uwm"
artifact_dirnames.KSERVE_CAPTURE_OPERATORS_STATE = "*__kserve__capture_operators_state"

IMPORTANT_FILES = [
    f"{artifact_dirnames.CLUSTER_DUMP_PROM_DB_DIR}/prometheus.t*",
    f"{artifact_dirnames.CLUSTER_DUMP_PROM_DB_DIR}/nodes.json",

    f"{artifact_dirnames.CLUSTER_DUMP_PROM_DB_UWM_DIR}/prometheus.t*",

    f"{artifact_dirnames.KSERVE_CAPTURE_OPERATORS_STATE}/_ansible.env",
    f"{artifact_dirnames.KSERVE_CAPTURE_OPERATORS_STATE}/ocp_version.yaml",
    f"{artifact_dirnames.KSERVE_CAPTURE_OPERATORS_STATE}/rhods.createdAt",
    f"{artifact_dirnames.KSERVE_CAPTURE_OPERATORS_STATE}/rhods.version",

    f"*/test_start_end.json", f"test_start_end.json",
    "config.yaml",
    ".uuid",
    ".matbench_prom_db_dir",
]

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
    results.test_config = _parse_test_config(dirname)


def _parse_once(results, dirname):
    results.metrics = _extract_metrics(dirname)

    # required to distinguish the control plane nodes
    results.nodes_info = _parse_nodes_info(dirname) or {}
    results.cluster_info = _extract_cluster_info(results.nodes_info)

    results.tests_timestamp = _find_test_timestamps(dirname)
    results.test_config = _parse_test_config(dirname)
    results.test_uuid = _parse_test_uuid(dirname)

    results.ocp_version = _parse_ocp_version(dirname)
    results.rhods_info = _parse_rhods_info(dirname)

    results.from_env = _parse_env(dirname, results.test_config)


def _extract_metrics(dirname):
    if artifact_paths.CLUSTER_DUMP_PROM_DB_DIR is None:
        logging.error(f"Couldn't find the Prom DB directory: {dirname / artifact_dirnames.CLUSTER_DUMP_PROM_DB_DIR}")
        return

    METRICS = {
        "sutest": (str(artifact_paths.CLUSTER_DUMP_PROM_DB_DIR / "prometheus.t*"), workload_prom.get_sutest_metrics()),
        #"uwm": (str(artifact_paths.CLUSTER_DUMP_PROM_DB_UWM_DIR / "prometheus.t*"), []),
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
def _parse_nodes_info(dirname, sutest_cluster=True):
    nodes_info = {}

    filename = artifact_paths.CLUSTER_DUMP_PROM_DB_DIR / "nodes.json"

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

        if node["metadata"]["labels"].get("nvidia.com/gpu.present"):
            node_info.gpu = types.SimpleNamespace()

            node_info.gpu.product = node["metadata"]["labels"].get("nvidia.com/gpu.product")
            node_info.gpu.memory = int(node["metadata"]["labels"].get("nvidia.com/gpu.memory")) / 1000
            node_info.gpu.count = int(node["metadata"]["labels"].get("nvidia.com/gpu.count"))
        else :
            node_info.gpu = None


    return nodes_info


def _extract_cluster_info(nodes_info):
    cluster_info = types.SimpleNamespace()

    cluster_info.node_count = [node_info for node_info in nodes_info.values() \
                                     if node_info.sutest_cluster]

    cluster_info.control_plane = [node_info for node_info in nodes_info.values() \
                                 if node_info.sutest_cluster and node_info.control_plane]

    cluster_info.infra = [node_info for node_info in nodes_info.values() \
                                if node_info.sutest_cluster and node_info.infra]

    cluster_info.gpus = []
    for infra_node in cluster_info.node_count:
        if not infra_node.gpu: continue
        cluster_info.gpus.append(infra_node.gpu)

    return cluster_info


def _find_test_timestamps(dirname):
    test_timestamps = []
    FILENAME = "test_start_end.json"
    logging.info(f"Searching for {FILENAME} ...")
    for test_timestamp_filename in sorted(dirname.glob(f"**/{FILENAME}")):

        with open(register_important_file(dirname, test_timestamp_filename.relative_to(dirname))) as f:
            try:
                data = json.load(f)
                test_timestamp = types.SimpleNamespace()
                start = data["start"].replace("Z", "+0000")
                test_timestamp.start = dateutil.parser.isoparse(start)
                end = data["end"]
                test_timestamp.end = dateutil.parser.isoparse(end)
                test_timestamp.settings = data["settings"]
                if "expe" in test_timestamp.settings:
                    del test_timestamp.settings["expe"]
                if "e2e_test" in test_timestamp.settings:
                    del test_timestamp.settings["e2e_test"]
                if "model_name" in test_timestamp.settings:
                    test_timestamp.settings["*model_name"] = test_timestamp.settings["model_name"]
                    del test_timestamp.settings["model_name"]

                test_timestamps.append(test_timestamp)
            except Exception as e:
                logging.warning(f"Failed to parse {test_timestamp_filename}: {e.__class__.__name__}: {e}")

    logging.info(f"Found {len(test_timestamps)}x {FILENAME}")
    return test_timestamps


def _parse_test_config(dirname):
    test_config = types.SimpleNamespace()

    filename = pathlib.Path("config.yaml")
    test_config.filepath = dirname / filename

    with open(register_important_file(dirname, filename)) as f:
        yaml_file = test_config.yaml_file = yaml.safe_load(f)

    if not yaml_file:
        logging.error(f"Config file '{filename}' is empty ...")
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
def _parse_test_uuid(dirname):
    with open(dirname / ".uuid") as f:
        test_uuid = f.read().strip()

    return uuid.UUID(test_uuid)


@ignore_file_not_found
def _parse_ocp_version(dirname):
    if not artifact_paths.KSERVE_CAPTURE_OPERATORS_STATE:
        logging.error(f"No '{artifact_dirnames.KSERVE_CAPTURE_OPERATORS_STATE}' directory found in {dirname} ...")
        return

    kserve_capture_operators_state_dir = artifact_paths.KSERVE_CAPTURE_OPERATORS_STATE[0] if isinstance(artifact_paths.KSERVE_CAPTURE_OPERATORS_STATE, list) else artifact_paths.KSERVE_CAPTURE_OPERATORS_STATE

    with open(register_important_file(dirname, kserve_capture_operators_state_dir / "ocp_version.yaml")) as f:
        sutest_ocp_version_yaml = yaml.safe_load(f)

    return sutest_ocp_version_yaml["openshiftVersion"]


@ignore_file_not_found
def _parse_rhods_info(dirname):
    if not artifact_paths.KSERVE_CAPTURE_OPERATORS_STATE:
        logging.error(f"No '{artifact_dirnames.KSERVE_CAPTURE_OPERATORS_STATE}' directory found in {dirname} ...")
        return

    rhods_info = types.SimpleNamespace()
    kserve_capture_operators_state_dir = artifact_paths.KSERVE_CAPTURE_OPERATORS_STATE[0] if isinstance(artifact_paths.KSERVE_CAPTURE_OPERATORS_STATE, list) else artifact_paths.KSERVE_CAPTURE_OPERATORS_STATE

    with open(register_important_file(dirname, kserve_capture_operators_state_dir / "rhods.version")) as f:
        rhods_info.version = f.read().strip()

    with open(register_important_file(dirname, kserve_capture_operators_state_dir / "rhods.createdAt")) as f:
        rhods_info.createdAt_raw = f.read().strip()

    try: rhods_info.createdAt = datetime.datetime.strptime(rhods_info.createdAt_raw, K8S_TIME_FMT)
    except ValueError as e:
        logging.error("Couldn't parse RHODS version timestamp: {e}")
        rhods_info.createdAt = None

    return rhods_info


@ignore_file_not_found
def _parse_env(dirname, test_config):
    from_env = types.SimpleNamespace()

    ansible_env = {}

    from_env.test = types.SimpleNamespace()
    from_env.test.run_id = None
    from_env.test.test_path = None
    from_env.test.ci_engine = None
    from_env.test.urls = {}

    capture_state_operators_dir = artifact_paths.KSERVE_CAPTURE_OPERATORS_STATE
    if isinstance(capture_state_operators_dir, list):
        capture_state_operators_dir = capture_state_operators_dir[-1]

    with open(register_important_file(dirname, capture_state_operators_dir / "_ansible.env")) as f:
        for line in f.readlines():
            k, _, v = line.strip().partition("=")

            ansible_env[k] = v


    # ---
    # eg 003__notebook_performance/003__sutest_notebooks__benchmark_performance/
    current_artifact_dir = pathlib.Path(ansible_env["ARTIFACT_DIR"])
    base_artifact_dir = "/logs/artifacts"

    if dirname.name == "from_url":
        with open(dirname / "source_url") as f: # not an important file
            source_url = f.read().strip()
        _prefix, _, from_env.test.test_path = source_url.partition(f"{from_env.test.run_id}/artifacts/")
    else:
        try:
            from_env.test.test_path = str((current_artifact_dir / dirname).relative_to(base_artifact_dir))
        except ValueError:
            from_env.test.test_path = str(dirname)


    if ansible_env.get("TOPSAIL_LOCAL_CI") == "true":
        from_env.test.ci_engine = "TOPSAIL_LOCAL_CI"
        from_env.test.run_id = ansible_env.get("TEST_RUN_IDENTIFIER")

        bucket_name = ansible_env.get("TOPSAIL_LOCAL_CI_BUCKET_NAME")
        job_name_safe = ansible_env.get("JOB_NAME_SAFE")

        from_env.test.urls |= dict(
            LOCAL_CI_S3=f"https://{bucket_name}.s3.amazonaws.com/index.html#local-ci/{job_name_safe}/{from_env.test.run_id}/{from_env.test.test_path}/",
        )


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

        from_env.test.run_id = f"{pull_number}/{job}/{build_id}/{test_name}"

        # ---
        from_env.test.urls |= dict(
            PROW_JOB=f"https://prow.ci.openshift.org/view/gs/test-platform-results/pr-logs/pull/{github_org}_{github_repo}/{pull_number}/{job}/{build_id}/",
            PROW_ARTIFACTS=f"https://gcsweb-ci.apps.ci.l2s4.p1.openshiftapps.com/gcs/test-platform-results/pr-logs/pull/{github_org}_{github_repo}/{pull_number}/{job}/{build_id}/artifacts/{test_name}/{step_name}/artifacts/{from_env.test.test_path}",
        )

    if ansible_env.get("PERFLAB_CI") == "true":
        from_env.test.ci_engine = "PERFLAB_CI"

        jumphost = ansible_env["JENKINS_JUMPHOST"]
        build_number = ansible_env["JENKINS_BUILD_NUMBER"]
        jenkins_job = ansible_env["JENKINS_JOB"] # "job/ExternalTeams/job/RHODS/job/topsail"
        jenkins_instance = ansible_env["JENKINS_INSTANCE"] # ci.app-svc-perf.corp.redhat.com

        from_env.test.run_id = build_number

        from_env.test.urls |= dict(
            JENKINS_ARTIFACTS=f"https://{jenkins_instance}/{jenkins_job}/{build_number}/artifact/run/{jumphost}/{from_env.test.test_path}"
        )

    if test_config.get("export_artifacts.enabled"):
        bucket = test_config.get("export_artifacts.bucket")
        path_prefix = test_config.get("export_artifacts.path_prefix")

        if ansible_env.get("OPENSHIFT_CI") == "true":
            job_spec = json.loads(os.environ["JOB_SPEC"])
            pull_number = job_spec["refs"]["pulls"][0]["number"]
            github_org = job_spec["refs"]["org"]
            github_repo = job_spec["refs"]["repo"]
            job = job_spec["job"]
            build_id = job_spec["buildid"]

            s3_path = f"prow/{pull_number}/{build_id}/test_ci"

        elif ansible_env.get("PERFLAB_CI") == "true":
            build_number = os.environ["JENKINS_BUILD_NUMBER"]
            job = os.environ["JENKINS_JOB"] # "job/ExternalTeams/job/RHODS/job/topsail"
            job_id = job[4:].replace("/job/", "_")

            s3_path = f"middleware_jenkins/{job_id}/{build_number}"

        from_env.test.urls |= dict(
            RHOAI_CPT_S3=f"https://{bucket}.s3.eu-central-1.amazonaws.com/index.html#{path_prefix}/{s3_path}/{from_env.test.test_path}/"
        )

    return from_env
