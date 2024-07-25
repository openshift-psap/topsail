import pathlib
import logging
import types
import pickle
import fnmatch
import os

import matrix_benchmarking.cli_args as cli_args
import matrix_benchmarking.store as store
import matrix_benchmarking.store.simple as store_simple

import projects.core.visualizations.helpers.store as core_helpers_store

from . import parsers
from . import lts_parser
from ..models import kpi as models_kpi

CACHE_FILENAME = "fine-tuning-prom.cache.pickle"
IMPORTANT_FILES = parsers.IMPORTANT_FILES
TEST_DIR_FILE = ".matbench_prom_db_dir"

IGNORE_EXIT_CODE = None

from ..models import lts as models_lts

local_store = core_helpers_store.BaseStore(
    cache_filename=CACHE_FILENAME, important_files=IMPORTANT_FILES,
    extra_mandatory_files=[TEST_DIR_FILE],
    artifact_dirnames=parsers.artifact_dirnames, artifact_paths=parsers.artifact_paths,

    parse_always=parsers.parse_always, parse_once=parsers.parse_once,

    lts_payload_model=models_lts.Payload,
    generate_lts_payload=lts_parser.generate_lts_payload,

    models_kpis=models_kpi.KPIs,
    get_kpi_labels=lts_parser.get_kpi_labels,
)

parsers.register_important_file = local_store.register_important_file
core_helpers_store.register_important_file = local_store.register_important_file
build_lts_payloads = local_store.build_lts_payloads
is_mandatory_file = local_store.is_mandatory_file
is_cache_file = local_store.is_cache_file
is_important_file = local_store.is_important_file

def _rewrite_settings(settings_dict):
    settings_dict.pop("hyper_parameters.raw_lists", None)

    container_image = settings_dict.pop("container_image", None)
    if container_image == "quay.io/modh/fms-hf-tuning:release-ec50c3d7dc09f50d9885f25efc3d2fc98a379709":
        container_image = "RHOAI 2.12 (rc)"
    elif container_image == "quay.io/modh/fms-hf-tuning:release-5e4e9441febdb5b2beb21eaecdda1103abd1db05":
        container_image = "RHOAI 2.11 (release)"
    elif container_image == "quay.io/modh/fms-hf-tuning:release-7a8ff0f4114ba43398d34fd976f6b17bb1f665f3":
        container_image = "RHOAI 2.10 (release)"

    if container_image:
        settings_dict["container_image"] = container_image

    return settings_dict

# ---
# --- custom store
# ---

def _duplicated_directory(import_key, old_location, new_location):
    logging.warning(f"duplicated results key: {import_key}")
    logging.warning(f"  old: {old_location}")
    logging.warning(f"  new: {new_location}")


def store_parse_directory(results_dir, expe, dirname):
    if not IGNORE_EXIT_CODE:
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
            return

        if exit_code != 0:
            logging.info(f"{dirname}: exit_code == {exit_code}, skipping ...")
            return


    with open(dirname / TEST_DIR_FILE) as f:
        name = f.read().strip()

    if not name:
        name = dirname.name

    import_settings = store_simple.parse_settings(dirname, name)

    def add_to_matrix(results, extra_settings=None):
        store.add_to_matrix(import_settings | (extra_settings or {}),
                            pathlib.Path(dirname),
                            results,
                            _duplicated_directory)

    try:
        logging.info(f"Parsing {dirname} ...")
        extra_settings__results = local_store.parse_directory(add_to_matrix, dirname, import_settings)
    except Exception as e:
        logging.error(f"Failed to parse {dirname} ...")
        logging.info(f"       {e.__class__.__name__}: {e}")
        logging.info("")
        raise e


def parse_data(results_dir=None):
    global IGNORE_EXIT_CODE
    IGNORE_EXIT_CODE = os.environ.get("MATBENCH_SIMPLE_STORE_IGNORE_EXIT_CODE", "false") == "true"

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
