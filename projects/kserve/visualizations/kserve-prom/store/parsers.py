import types
import logging
import json

import dateutil.parser

import projects.core.visualizations.helpers.store.parsers as core_helpers_store_parsers

from . import prom as workload_prom

register_important_file = None # will be when importing store/__init__.py

artifact_dirnames = types.SimpleNamespace()
artifact_dirnames.CLUSTER_DUMP_PROM_DB_DIR = "*__cluster__dump_prometheus_dbs/*__cluster__dump_prometheus_db"
artifact_dirnames.CLUSTER_DUMP_PROM_DB_UWM_DIR = "*__cluster__dump_prometheus_dbs/*__cluster__dump_prometheus_db_uwm"
artifact_dirnames.KSERVE_CAPTURE_OPERATORS_STATE = "*__kserve__capture_operators_state"
artifact_paths = types.SimpleNamespace()

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



def parse_always(results, dirname, import_settings):
    # parsed even when reloading from the cache file
    pass


def parse_once(results, dirname):
    results.metrics = _extract_metrics(dirname)

    results.test_uuid = core_helpers_store_parsers.parse_test_uuid(dirname)
    results.test_config = core_helpers_store_parsers.parse_test_config(dirname)
    results.tests_timestamp = _find_test_timestamps(dirname)

    capture_state_dir = artifact_paths.KSERVE_CAPTURE_OPERATORS_STATE
    results.nodes_info = core_helpers_store_parsers.parse_nodes_info(dirname, capture_state_dir) or {}
    results.cluster_info = core_helpers_store_parsers.extract_cluster_info(results.nodes_info)

    results.ocp_version = core_helpers_store_parsers.parse_ocp_version(dirname, capture_state_dir)
    results.rhods_info = core_helpers_store_parsers.parse_rhods_info(dirname, capture_state_dir)

    results.from_env = core_helpers_store_parsers.parse_env(dirname, results.test_config, capture_state_dir)


def _extract_metrics(dirname):
    if artifact_paths.CLUSTER_DUMP_PROM_DB_DIR is None:
        logging.error(f"Couldn't find the Prom DB directory: {dirname / artifact_dirnames.CLUSTER_DUMP_PROM_DB_DIR}")
        return

    db_files = {
        "sutest": (str(artifact_paths.CLUSTER_DUMP_PROM_DB_DIR / "prometheus.t*"), workload_prom.get_sutest_metrics()),
        #"uwm": (str(artifact_paths.CLUSTER_DUMP_PROM_DB_UWM_DIR / "prometheus.t*"), []),
    }

    return core_helpers_store_parsers.extract_metrics(dirname, db_files)


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
