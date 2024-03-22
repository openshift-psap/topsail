import types
import pathlib
import logging
import yaml
import os
import json
import datetime
from collections import defaultdict
import dateutil.parser
import urllib.parse
import uuid
from functools import reduce

import matrix_benchmarking.cli_args as cli_args
import matrix_benchmarking.store.prom_db as store_prom_db

from . import prom as workload_prom
from . import lts_parser

register_important_file = None # will be when importing store/__init__.py

K8S_TIME_FMT = "%Y-%m-%dT%H:%M:%SZ"
SHELL_DATE_TIME_FMT = "%a %b %d %H:%M:%S %Z %Y"
ANSIBLE_LOG_DATE_TIME_FMT = "%Y-%m-%d %H:%M:%S"

artifact_dirnames = types.SimpleNamespace()
artifact_dirnames.LLM_LOAD_TEST_RUN_DIR = "*__llm_load_test__run"
artifact_dirnames.KSERVE_CAPTURE_STATE = "*__kserve__capture_state"

IMPORTANT_FILES = [
    "config.yaml",
    ".uuid",

    f"{artifact_dirnames.LLM_LOAD_TEST_RUN_DIR}/output/output.json",
    f"{artifact_dirnames.LLM_LOAD_TEST_RUN_DIR}/src/llm_load_test.config.yaml",
    f"{artifact_dirnames.KSERVE_CAPTURE_STATE}/_ansible.env",
    f"{artifact_dirnames.KSERVE_CAPTURE_STATE}/pods.json",
    f"{artifact_dirnames.KSERVE_CAPTURE_STATE}/ocp_version.yaml",
    f"{artifact_dirnames.KSERVE_CAPTURE_STATE}/rhods.createdAt",
    f"{artifact_dirnames.KSERVE_CAPTURE_STATE}/rhods.version",
    f"{artifact_dirnames.KSERVE_CAPTURE_STATE}/serving.json",
    f"{artifact_dirnames.KSERVE_CAPTURE_STATE}/nodes.json",
]

def ignore_file_not_found(fn):
    def decorator(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except FileNotFoundError as e:
            logging.warning(f"{fn.__name__}: FileNotFoundError: {e}")
            return None

    return decorator

def get_from_path(d, path, default=None):
    result = default
    try:
        result = reduce(dict.get, path.split("."), d)
    finally:
        return result


def _parse_always(results, dirname, import_settings):
    # parsed even when reloading from the cache file
    from . import get_yaml_get_key
    results.llm_load_test_config.get = get_yaml_get_key("llm-load-test config file", results.llm_load_test_config.yaml_file)

    results.test_config.get = get_yaml_get_key("topsail config file", results.test_config.yaml_file)

    results.from_local_env = _parse_local_env(dirname)
    results.lts = lts_parser.generate_lts_payload(results, import_settings, must_validate=False)


def _parse_once(results, dirname):
    results.test_config = _parse_test_config(dirname)

    results.llm_load_test_config = _parse_llm_load_test_config(dirname)
    results.llm_load_test_output = _parse_llm_load_test_output(dirname)
    results.predictor_logs = _parse_predictor_logs(dirname)
    results.predictor_pod = _parse_predictor_pod(dirname)
    results.inference_service = _parse_inference_service(dirname)
    results.test_start_end = _parse_test_start_end(dirname, results.llm_load_test_output)
    results.ocp_version = _parse_ocp_version(dirname)
    results.rhods_info = _parse_rhods_info(dirname)
    results.test_uuid = _parse_test_uuid(dirname)
    results.from_env = _parse_env(dirname, results.test_config)
    results.nodes_info = _parse_nodes_info(dirname)


def _parse_local_env(dirname):
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
        logging.warning(f"Unknown execution environment: JOB_NAME_SAFE={job_name} ARTIFACT_DIR={os.environ.get('ARTIFACT_DIR')}")
        from_local_env.artifacts_basedir = dirname.absolute()

    return from_local_env


def _parse_test_config(dirname):
    test_config = types.SimpleNamespace()

    filename = pathlib.Path("config.yaml")
    test_config.filepath = dirname / filename

    with open(register_important_file(dirname, filename)) as f:
        yaml_file = test_config.yaml_file = yaml.safe_load(f)

    if not yaml_file:
        logging.error(f"Config file '{filename}' is empty ...")
        yaml_file = test_config.yaml_file = {}

    from . import get_yaml_get_key

    test_config.get = get_yaml_get_key("topsail config", yaml_file)

    return test_config


@ignore_file_not_found
def _parse_llm_load_test_output(dirname):
    llm_output_file = dirname / artifact_paths.LLM_LOAD_TEST_RUN_DIR / "output" / "output.json"
    register_important_file(dirname, llm_output_file.relative_to(dirname))

    with open(llm_output_file) as f:
        llm_load_test_output = json.load(f)

    return llm_load_test_output

@ignore_file_not_found
def _parse_llm_load_test_config(dirname):
    llm_config_file = dirname / artifact_paths.LLM_LOAD_TEST_RUN_DIR / "src" / "llm_load_test.config.yaml"
    register_important_file(dirname, llm_config_file.relative_to(dirname))

    llm_load_test_config = types.SimpleNamespace()

    with open(llm_config_file) as f:
        yaml_file = llm_load_test_config.yaml_file = yaml.safe_load(f)

    if not yaml_file:
        logging.error(f"Config file '{llm_config_file}' is empty ...")
        yaml_file = llm_load_test_config.yaml_file = {}

    from . import get_yaml_get_key

    llm_load_test_config.get = get_yaml_get_key("llm-load-test config", yaml_file)

    return llm_load_test_config

@ignore_file_not_found
def _parse_inference_service(dirname):
    if not artifact_paths.KSERVE_CAPTURE_STATE:
        logging.error(f"No '{artifact_dirnames.KSERVE_CAPTURE_STATE}' directory found in {dirname} ...")
        return

    capture_state_dir = artifact_paths.KSERVE_CAPTURE_STATE
    if isinstance(capture_state_dir, list):
        capture_state_dir = capture_state_dir[-1]

    inference_service = types.SimpleNamespace()
    serving_file = capture_state_dir / "serving.json"

    if (dirname / serving_file).exists():
        with open(register_important_file(dirname, serving_file)) as f:
            serving_def = json.load(f)

    if not serving_def["items"]:
        logging.error(f"No InferenceService found in {serving_file} ...")
        return inference_service

    inference_service_specs = [item for item in serving_def["items"] if item["kind"] == "InferenceService"]
    inference_service_specs = inference_service_specs[0]

    inference_service.min_replicas = get_from_path(inference_service_specs, "spec.predictor.minReplicas", default=None)
    inference_service.max_replicas = get_from_path(inference_service_specs, "spec.predictor.maxReplicas", default=None)

    return inference_service


@ignore_file_not_found
def _parse_predictor_pod(dirname):
    if not artifact_paths.KSERVE_CAPTURE_STATE:
        logging.error(f"No '{artifact_dirnames.KSERVE_CAPTURE_STATE}' directory found in {dirname} ...")
        return

    capture_state_dir = artifact_paths.KSERVE_CAPTURE_STATE
    if isinstance(capture_state_dir, list):
        capture_state_dir = capture_state_dir[-1]

    predictor_pod = types.SimpleNamespace()
    pods_def_file = capture_state_dir / "pods.json"

    if (dirname / pods_def_file).exists():
        with open(register_important_file(dirname, pods_def_file)) as f:
            pods_def = json.load(f)
    else:
        pods_def_file = pods_def_file.with_suffix(".yaml")
        with open(register_important_file(dirname, pods_def_file)) as f:
            logging.warning("Loading the predictor pod def as yaml ... (json file missing)")
            pods_def = yaml.safe_load(f)

    if not pods_def["items"]:
        logging.error(f"No container Pod found in {pods_def_file} ...")
        return predictor_pods

    pod = pods_def["items"][0]

    condition_times = {}
    for condition in pod["status"]["conditions"]:
        condition_times[condition["type"]] = \
            datetime.datetime.strptime(
                condition["lastTransitionTime"], K8S_TIME_FMT)

    containers_start_time = {}
    for container_status in pod["status"]["containerStatuses"]:
        try:
            containers_start_time[container_status["name"]] = \
                datetime.datetime.strptime(
                    container_status["state"]["running"]["startedAt"], K8S_TIME_FMT)
        except KeyError: pass # container not running


    predictor_pod.init_time = condition_times["Initialized"] - condition_times["PodScheduled"]
    predictor_pod.load_time = condition_times["Ready"] - condition_times["Initialized"]

    for container in pod["spec"]["containers"]:
        if container["name"] != "kserve-container": continue
        try:
            gpu_count = int(container["resources"]["requests"]["nvidia.com/gpu"])
        except:
            gpu_count = 0
        break
    else:
        logging.warning("Container 'kserve-container' not found in the predictor pod spec ...")
        gpu_count = None

    predictor_pod.gpu_count = gpu_count

    return predictor_pod


@ignore_file_not_found
def _parse_predictor_logs(dirname):
    if not artifact_paths.KSERVE_CAPTURE_STATE:
        logging.error(f"No '{artifact_dirnames.KSERVE_CAPTURE_STATE}' directory found in {dirname} ...")
        return

    kserve_capture_state_dir = artifact_paths.KSERVE_CAPTURE_STATE[-1] if isinstance(artifact_paths.KSERVE_CAPTURE_STATE, list) else artifact_paths.KSERVE_CAPTURE_STATE

    predictor_logs = types.SimpleNamespace()
    predictor_logs.distribution = defaultdict(int)
    predictor_logs.line_count = 0

    for log_file in (dirname / kserve_capture_state_dir).glob("logs/*.log"):

        for line in open(log_file).readlines():
            predictor_logs.line_count += 1

            if '"severity":"ERROR"' in line:
                predictor_logs.distribution["errors"] += 1
            if '"channel": "DESTROY-THRD"' in line:
                predictor_logs.distribution["DESTROY-THRD"] += 1
            if '"channel": "ABORT-ACTION"' in line:
                predictor_logs.distribution["ABORT-ACTION"] += 1

    return predictor_logs


def _parse_test_start_end(dirname, llm_load_test_output):
    if not llm_load_test_output:
        return None

    test_start_end = types.SimpleNamespace()
    test_start_end.start = None
    test_start_end.end = None

    for result in llm_load_test_output.get("results") or []:
        start = datetime.datetime.fromtimestamp(result["start_time"])
        end = datetime.datetime.fromtimestamp(result["end_time"])

        if test_start_end.start is None or start < test_start_end.start:
            test_start_end.start = start

        if test_start_end.end is None or end > test_start_end.end:
            test_start_end.end = end

    if test_start_end.start is None:
        logging.warning("Could not find the start time of the test...")
    if test_start_end.end is None:
        logging.warning("Could not find the end time of the test...")

    return test_start_end


@ignore_file_not_found
def _parse_ocp_version(dirname):
    if not artifact_paths.KSERVE_CAPTURE_STATE:
        logging.error(f"No '{artifact_dirnames.KSERVE_CAPTURE_STATE}' directory found in {dirname} ...")
        return

    kserve_capture_state_dir = artifact_paths.KSERVE_CAPTURE_STATE[0] if isinstance(artifact_paths.KSERVE_CAPTURE_STATE, list) else artifact_paths.KSERVE_CAPTURE_STATE

    with open(register_important_file(dirname, kserve_capture_state_dir / "ocp_version.yaml")) as f:
        sutest_ocp_version_yaml = yaml.safe_load(f)

    return sutest_ocp_version_yaml["openshiftVersion"]


@ignore_file_not_found
def _parse_rhods_info(dirname):
    if not artifact_paths.KSERVE_CAPTURE_STATE:
        logging.error(f"No '{artifact_dirnames.KSERVE_CAPTURE_STATE}' directory found in {dirname} ...")
        return

    rhods_info = types.SimpleNamespace()
    kserve_capture_state_dir = artifact_paths.KSERVE_CAPTURE_STATE[0] if isinstance(artifact_paths.KSERVE_CAPTURE_STATE, list) else artifact_paths.KSERVE_CAPTURE_STATE

    with open(register_important_file(dirname, kserve_capture_state_dir / "rhods.version")) as f:
        rhods_info.version = f.read().strip()

    with open(register_important_file(dirname, kserve_capture_state_dir / "rhods.createdAt")) as f:
        rhods_info.createdAt_raw = f.read().strip()

    try: rhods_info.createdAt = datetime.datetime.strptime(rhods_info.createdAt_raw, K8S_TIME_FMT)
    except ValueError as e:
        logging.error("Couldn't parse RHODS version timestamp: {e}")
        rhods_info.createdAt = None

    return rhods_info

@ignore_file_not_found
def _parse_nodes_info(dirname):
    if not artifact_paths.KSERVE_CAPTURE_STATE:
        logging.error(f"No '{artifact_dirnames.KSERVE_CAPTURE_STATE}' directory found in {dirname} ...")
        return

    capture_state_dir = artifact_paths.KSERVE_CAPTURE_STATE
    if isinstance(capture_state_dir, list):
        capture_state_dir = capture_state_dir[-1]

    nodes_info = {}

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


@ignore_file_not_found
def _parse_test_uuid(dirname):
    with open(dirname / ".uuid") as f:
        test_uuid = f.read().strip()

    return uuid.UUID(test_uuid)


@ignore_file_not_found
def _parse_env(dirname, test_config):
    from_env = types.SimpleNamespace()

    ansible_env = {}

    from_env.test = types.SimpleNamespace()
    from_env.test.run_id = None
    from_env.test.test_path = None
    from_env.test.ci_engine = None
    from_env.test.urls = {}

    capture_state_dir = artifact_paths.KSERVE_CAPTURE_STATE
    if isinstance(capture_state_dir, list):
        capture_state_dir = capture_state_dir[-1]

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
        from_env.test.test_path = str((current_artifact_dir / dirname).relative_to(base_artifact_dir))


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
