import types
import logging
import json
import yaml

import dateutil.parser

import projects.matrix_benchmarking.visualizations.helpers.store.parsers as helpers_store_parsers
import projects.matrix_benchmarking.visualizations.helpers.store as helpers_store

from . import prom as workload_prom

register_important_file = None # will be when importing store/__init__.py

artifact_dirnames = types.SimpleNamespace()
artifact_dirnames.CLUSTER_DUMP_PROM_DB_DIR = "*__cluster__dump_prometheus_dbs/*__cluster__dump_prometheus_db"
#artifact_dirnames.CLUSTER_DUMP_PROM_DB_UWM_DIR = "*__cluster__dump_prometheus_dbs/*__cluster__dump_prometheus_db_uwm"
artifact_dirnames.KSERVE_CAPTURE_OPERATORS_STATE = "*__kserve__capture_operators_state"
artifact_dirnames.KSERVE_CAPTURE_STATE = "*__kserve__capture_state"
artifact_dirnames.LLM_LOAD_TEST_RUN_DIR = "**/*__llm_load_test__run"

artifact_paths = types.SimpleNamespace()

IMPORTANT_FILES = [
    f"{artifact_dirnames.CLUSTER_DUMP_PROM_DB_DIR}/prometheus.t*",
    f"{artifact_dirnames.CLUSTER_DUMP_PROM_DB_DIR}/nodes.json",

    #f"{artifact_dirnames.CLUSTER_DUMP_PROM_DB_UWM_DIR}/prometheus.t*",

    f"{artifact_dirnames.KSERVE_CAPTURE_OPERATORS_STATE}/_ansible.env",
    f"{artifact_dirnames.KSERVE_CAPTURE_OPERATORS_STATE}/ocp_version.yaml",
    f"{artifact_dirnames.KSERVE_CAPTURE_OPERATORS_STATE}/rhods.createdAt",
    f"{artifact_dirnames.KSERVE_CAPTURE_OPERATORS_STATE}/rhods.version",
    f"{artifact_dirnames.KSERVE_CAPTURE_OPERATORS_STATE}/nodes.json",
    f"{artifact_dirnames.KSERVE_CAPTURE_STATE}/serving.json",
    f"{artifact_dirnames.LLM_LOAD_TEST_RUN_DIR}/src/llm_load_test.config.yaml",

    f"*/test_start_end.json", f"test_start_end.json",
    "config.yaml",
    ".uuid",
    ".matbench_prom_db_dir",
]



def parse_always(results, dirname, import_settings):
    # parsed even when reloading from the cache file
    pass


def parse_once(results, dirname):
    results.metrics = _extract_metrics(dirname)

    results.test_uuid = helpers_store_parsers.parse_test_uuid(dirname)
    results.test_config = helpers_store_parsers.parse_test_config(dirname)
    results.tests_timestamp = _find_test_timestamps(dirname)

    capture_state_dir = artifact_paths.KSERVE_CAPTURE_OPERATORS_STATE
    results.nodes_info = helpers_store_parsers.parse_nodes_info(dirname, capture_state_dir) or {}
    results.cluster_info = helpers_store_parsers.extract_cluster_info(results.nodes_info)

    results.ocp_version = helpers_store_parsers.parse_ocp_version(dirname, capture_state_dir)
    results.rhods_info = helpers_store_parsers.parse_rhods_info(dirname, capture_state_dir, results.test_config.get("rhods.catalog.version_name"))

    results.from_env = helpers_store_parsers.parse_env(dirname, results.test_config, capture_state_dir)

    results.inference_service = _parse_inference_service(dirname)
    results.llm_load_test_config = _parse_llm_load_test_config(dirname)

def _extract_metrics(dirname):
    if artifact_paths.CLUSTER_DUMP_PROM_DB_DIR is None:
        logging.error(f"Couldn't find the Prom DB directory: {dirname / artifact_dirnames.CLUSTER_DUMP_PROM_DB_DIR}")
        return

    db_files = {
        "sutest": (str(artifact_paths.CLUSTER_DUMP_PROM_DB_DIR / "prometheus.t*"), workload_prom.get_sutest_metrics()),
        #"uwm": (str(artifact_paths.CLUSTER_DUMP_PROM_DB_UWM_DIR / "prometheus.t*"), []),
    }

    return helpers_store_parsers.extract_metrics(dirname, db_files)


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


@helpers_store_parsers.ignore_file_not_found
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

    inference_service.min_replicas = helpers_store_parsers.dict_get_from_path(inference_service_specs, "spec.predictor.minReplicas", default=None)
    inference_service.max_replicas = helpers_store_parsers.dict_get_from_path(inference_service_specs, "spec.predictor.maxReplicas", default=None)

    return inference_service


@helpers_store_parsers.ignore_file_not_found
def _parse_llm_load_test_config(dirname):
    if not artifact_paths.LLM_LOAD_TEST_RUN_DIR:
        return None

    llm_config_file = dirname / artifact_paths.LLM_LOAD_TEST_RUN_DIR / "src" / "llm_load_test.config.yaml"
    register_important_file(dirname, llm_config_file.relative_to(dirname))

    llm_load_test_config = types.SimpleNamespace()

    with open(llm_config_file) as f:
        yaml_file = llm_load_test_config.yaml_file = yaml.safe_load(f)

    if not yaml_file:
        logging.error(f"Config file '{llm_config_file}' is empty ...")
        yaml_file = llm_load_test_config.yaml_file = {}

    llm_load_test_config.name = f"llm-load-test config {llm_config_file}"
    llm_load_test_config.get = helpers_store.get_yaml_get_key(llm_load_test_config.name, yaml_file)

    return llm_load_test_config
