import types
import logging
import uuid
import pathlib
import datetime
import yaml
import json
import os
from functools import reduce
import urllib

import matrix_benchmarking.store.prom_db as store_prom_db
import matrix_benchmarking.cli_args as cli_args

import projects.matrix_benchmarking.visualizations.helpers.store as helpers_store
from . import k8s_quantity

K8S_TIME_FMT = "%Y-%m-%dT%H:%M:%SZ"
K8S_TIME_MILLI_FMT = "%Y-%m-%dT%H:%M:%S.%fZ"
SHELL_DATE_TIME_FMT = "%a %b %d %H:%M:%S %Z %Y"
ANSIBLE_LOG_DATE_TIME_FMT = "%Y-%m-%d %H:%M:%S"

register_important_file = lambda dirname, filename: dirname/filename

def ignore_file_not_found(fn):
    def decorator(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except FileNotFoundError as e:
            logging.warning(f"{fn.__name__}: FileNotFoundError: {e}")
            return None

    return decorator


def dict_get_from_path(dict_obj, path, default=None):
    # default currently unused :/
    return reduce(dict.get, path.split("."), dict_obj)


@ignore_file_not_found
def parse_env(dirname, test_config, capture_state_dir):
    from_env = types.SimpleNamespace()

    ansible_env = {}

    from_env.test = types.SimpleNamespace()
    from_env.test.run_id = None
    from_env.test.test_path = None
    from_env.test.ci_engine = None
    from_env.test.urls = {}

    if not capture_state_dir:
        logging.warning("no capture_state_dir received. Cannot parse the execution environment.")
        return from_env

    with open(register_important_file(dirname, capture_state_dir / "_ansible.env")) as f:
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
            if str(current_artifact_dir).endswith(str(dirname)):
                base = pathlib.Path(str(current_artifact_dir).replace(str(dirname), ""))
                from_env.test.test_path = str((base / dirname).relative_to(base_artifact_dir))
            else:
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

    if test_config.get("export_artifacts.enabled", False):
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
            if os.environ.get("PERFLAB_CI") == "true":
                build_number = os.environ["JENKINS_BUILD_NUMBER"]
                job = os.environ["JENKINS_JOB"]  # "job/ExternalTeams/job/RHODS/job/topsail"
            else:
                build_number = "---"
                job = "job/ExternalTeams/job/RHODS/job/topsail"

            job_id = job[4:].replace("/job/", "_")

            s3_path = f"middleware_jenkins/{job_id}/{build_number}"

        elif ansible_env.get("TOPSAIL_LOCAL_CI") == "true":
            test_identifier = ansible_env.get("TEST_RUN_IDENTIFIER")
            s3_path = f"{test_identifier}"

        from_env.test.urls |= dict(
            RHOAI_CPT_S3=f"https://{bucket}.s3.eu-central-1.amazonaws.com/index.html#{path_prefix}/{s3_path}/{from_env.test.test_path}/"
        )

    return from_env


@ignore_file_not_found
def parse_test_uuid(dirname):
    with open(dirname / ".uuid") as f:
        test_uuid = f.read().strip()

    return uuid.UUID(test_uuid)


@ignore_file_not_found
def parse_nodes_info(dirname, capture_state_dir, sutest_cluster=True):
    nodes_info = {}

    if not capture_state_dir:
        logging.warning("no capture_state_dir received. Cannot parse the node information.")
        return nodes_info

    nodes_file = capture_state_dir / "nodes.json"
    with open(register_important_file(dirname, nodes_file)) as f:
        nodeList = json.load(f)

    if not nodeList["items"]:
        logging.error(f"No nodes found in {nodes_file} ...")
        return None

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
            product = node["metadata"]["labels"].get("nvidia.com/gpu.product")
            if not product:
                node_info.gpu = None
                continue

            node_info.gpu = types.SimpleNamespace()

            node_info.gpu.product = product
            if node["metadata"]["labels"].get("nvidia.com/gpu.memory"):
                node_info.gpu.memory = int(node["metadata"]["labels"].get("nvidia.com/gpu.memory")) / 1000
            if node["metadata"]["labels"].get("nvidia.com/gpu.count"):
                node_info.gpu.count = int(node["metadata"]["labels"].get("nvidia.com/gpu.count"))

        else :
            node_info.gpu = None

        node_info.allocatable = types.SimpleNamespace()
        node_info.allocatable.memory = float(k8s_quantity.parse_quantity(node["status"]["allocatable"]["memory"]))
        node_info.allocatable.memory = float(k8s_quantity.parse_quantity(node["status"]["allocatable"]["memory"]))
        node_info.allocatable.cpu = float(k8s_quantity.parse_quantity(node["status"]["allocatable"]["cpu"]))

        node_info.allocatable.gpu = int(node["status"]["allocatable"].get("nvidia.com/gpu", 0))
        node_info.allocatable.__dict__["nvidia.com/gpu"] = node_info.allocatable.gpu

    return nodes_info


def extract_cluster_info(nodes_info):
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


@ignore_file_not_found
def parse_rhods_info(dirname, capture_state_dir, version_name=None):
    rhods_info = types.SimpleNamespace()

    with open(register_important_file(dirname, capture_state_dir / "rhods.version")) as f:
        rhods_info.version = f.read().strip()

    with open(register_important_file(dirname, capture_state_dir / "rhods.createdAt")) as f:
        rhods_info.createdAt_raw = f.read().strip()

    try: rhods_info.createdAt = datetime.datetime.strptime(rhods_info.createdAt_raw, K8S_TIME_FMT)
    except ValueError as e:
        logging.error("Couldn't parse RHOAI version timestamp: {e}")
        rhods_info.createdAt = None

    if version_name:
        rhods_info.full_version = f"{rhods_info.version}-{version_name}+{rhods_info.createdAt.strftime('%Y-%m-%d')}"
    else:
        logging.info("parse_rhods_info: no version_name provided.")
        rhods_info.full_version = None

    return rhods_info


@ignore_file_not_found
def parse_ocp_version(dirname, capture_state_dir):
    if not capture_state_dir:
        logging.warning("no capture_state_dir received. Cannot parse OCP version")
        return ""

    ocp_version_files = list((dirname / capture_state_dir).glob("ocp_version.y*ml"))

    if not ocp_version_files:
        raise FileNotFoundError(f"no 'ocp_version.y*ml' in {dirname / capture_state_dir}")
    ocp_version_file = ocp_version_files[0]

    with open(register_important_file(dirname, capture_state_dir / ocp_version_file.name)) as f:
        sutest_ocp_version_yaml = yaml.safe_load(f)

    return sutest_ocp_version_yaml["openshiftVersion"]


def parse_test_config(dirname):
    test_config = types.SimpleNamespace()

    filename = pathlib.Path("config.yaml")
    test_config.filepath = dirname / filename

    with open(register_important_file(dirname, filename)) as f:
        yaml_file = test_config.yaml_file = yaml.safe_load(f)

    if not yaml_file:
        logging.error(f"Config file '{filename}' is empty ...")
        yaml_file = test_config.yaml_file = {}

    test_config.name = f"topsail config ({test_config.filepath})"
    test_config.get = helpers_store.get_yaml_get_key(test_config.name, yaml_file)

    return test_config


def parse_local_env(dirname):
    from_local_env = types.SimpleNamespace()

    from_local_env.artifacts_basedir = None
    from_local_env.source_url = None
    from_local_env.is_interactive = False

    try:
        with open(dirname / "source_url") as f: # not an important file
            from_local_env.source_url = f.read().strip()
            from_local_env.artifacts_basedir = pathlib.Path(urllib.parse.urlparse(from_local_env.source_url).path)
    except FileNotFoundError as e:
        pass

    logging.debug(f"Source_url: {from_local_env.source_url}, artifacts_basedir: {from_local_env.artifacts_basedir}")

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
        from_local_env.artifacts_basedir = dirname.absolute()

    return from_local_env


def extract_metrics(dirname, db_files):
    metrics = {}
    for name, (tarball_glob, metric) in db_files.items():
        try:
            prom_tarball = list(dirname.glob(tarball_glob))[0]
        except IndexError:
            logging.warning(f"No {tarball_glob} in '{dirname}'.")
            continue

        register_important_file(dirname, prom_tarball.relative_to(dirname))
        metrics[name] = store_prom_db.extract_metrics(prom_tarball, metric, dirname)

    return metrics
