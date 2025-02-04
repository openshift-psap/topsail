import pathlib
import logging
import types
import pickle
import fnmatch
import os

import matrix_benchmarking.cli_args as cli_args
import matrix_benchmarking.store as store
import matrix_benchmarking.store.simple as store_simple

import projects.matrix_benchmarking.visualizations.helpers.store as helpers_store

RAY_FLAVOR = "ray_prom"
FMS_FLAVOR = "fms_prom"
ILAB_FLAVOR = "ilab_prom"
SUPPORTED_FLAVORS = (RAY_FLAVOR, FMS_FLAVOR, ILAB_FLAVOR)
FLAVOR = __package__.split(".")[-2]
if FLAVOR == "fine_tuning_prom":
    raise ValueError(f"Please use a supported flavor of the fine_tuning" +
                     f" workload visualization ({', '.join(SUPPORTED_FLAVORS)})")
elif FLAVOR not in SUPPORTED_FLAVORS:
    raise ValueError(f"{FLAVOR} is not a supported flavor of the fine_tuning" +
                     f" workload visualization ({', '.join(SUPPORTED_FLAVORS)}). Received {FLAVOR}.")

logging.info(f"Running with the {FLAVOR} of the fine_tuning visualization package.")

### (keep this below the FLAVOR lookup, so that it can be used)

from . import parsers
from . import fms_lts_parser, ilab_lts_parser
from ..models import fms_kpi, ilab_kpi

CACHE_FILENAME = "fine-tuning-prom.cache.pickle"
IMPORTANT_FILES = parsers.IMPORTANT_FILES
TEST_DIR_FILE = ".matbench_prom_db_dir"

from ..models import fms_lts, ilab_lts

store_conf = dict()
if FLAVOR == FMS_FLAVOR:
    store_conf |= dict(
        lts_payload_model=fms_lts.Payload,
        generate_lts_payload=fms_lts_parser.generate_lts_payload,

        models_kpis=fms_kpi.KPIs,
        get_kpi_labels=fms_lts_parser.get_kpi_labels,
    )
elif FLAVOR == ILAB_FLAVOR:
    store_conf |= dict(
        lts_payload_model=ilab_lts.Payload,
        generate_lts_payload=ilab_lts_parser.generate_lts_payload,

        models_kpis=ilab_kpi.KPIs,
        get_kpi_labels=ilab_lts_parser.get_kpi_labels,
    )
else:
    # not LTS/KPI configuration for the other flavors, for the time being.
    pass

local_store = helpers_store.BaseStore(
    cache_filename=CACHE_FILENAME,
    important_files=IMPORTANT_FILES,
    extra_mandatory_files=[TEST_DIR_FILE],

    artifact_dirnames=parsers.artifact_dirnames,
    artifact_paths=parsers.artifact_paths,

    parse_always=parsers.parse_always,
    parse_once=parsers.parse_once,

    **store_conf
)

parsers.register_important_file = local_store.register_important_file
helpers_store.register_important_file = local_store.register_important_file
build_lts_payloads = local_store.build_lts_payloads
is_mandatory_file = local_store.is_mandatory_file
is_cache_file = local_store.is_cache_file
is_important_file = local_store.is_important_file

def _rewrite_settings(settings_dict):
    settings_dict.pop("hyper_parameters.raw_lists", None)
    settings_dict.pop("hyper_parameters", None)

    return settings_dict

# ---
# --- custom store
# ---

def _duplicated_directory(import_key, old_entry, old_location, results, new_location):
    logging.warning(f"duplicated results key: {import_key}")
    logging.warning(f"  old: {old_location}")
    logging.warning(f"  new: {new_location}")


def store_parse_directory(results_dir, expe, dirname):
    try:
        with open(dirname / "exit_code") as f:
            content = f.read().strip()
            if not content:
                logging.info(f"{dirname}: exit_code is empty, skipping ...")
                return

        exit_code = int(content)
    except FileNotFoundError as e:
        exit_code = 404

    except Exception as e:
        logging.info(f"{dirname}: exit_code cannot be read/parsed, skipping ... ({e})")
        exit_code = -1

    import_settings = store_simple.parse_settings(dirname)

    def add_to_matrix(results, extra_settings=None):
        store.add_to_matrix(import_settings | (extra_settings or {}),
                            pathlib.Path(dirname),
                            results, exit_code,
                            _duplicated_directory)

    try:
        logging.info(f"Parsing {dirname} ...")
        extra_settings__results = local_store.parse_directory(add_to_matrix, dirname, import_settings, exit_code)
    except Exception as e:
        logging.error(f"Failed to parse {dirname} ...")
        logging.info(f"       {e.__class__.__name__}: {e}")
        logging.info("")
        raise e


def parse_data(results_dir=None):
    store.register_custom_rewrite_settings(_rewrite_settings)

    if results_dir is None:
        results_dir = pathlib.Path(cli_args.kwargs["results_dirname"])

    logging.info(f"Searching '{results_dir}' for files named '{TEST_DIR_FILE}' ...")
    results_directories = []
    path = os.walk(results_dir, followlinks=True)
    results_directories = []
    for _this_dir, directories, files in path:
        if TEST_DIR_FILE not in files: continue
        if "skip" in files: continue
        this_dir = pathlib.Path(_this_dir)

        is_subdir_of_results_dir = False
        for existing_results_directory in results_directories:
            if existing_results_directory in this_dir.parents:
                is_subdir_of_results_dir = True
                break
        if is_subdir_of_results_dir:
            # we don't want nested results dirs
            continue


        results_directories.append(this_dir)

        expe = "expe"
        store_parse_directory(results_dir, expe, this_dir)
