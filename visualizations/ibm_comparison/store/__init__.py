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

from . import parsers
from . import lts_parser

CACHE_FILENAME = "cache.pickle"
IMPORTANT_FILES = parsers.IMPORTANT_FILES
TEST_DIR_FILE = ".ibm_cmp_dir"

local_store = helpers_store.BaseStore(
    cache_filename=CACHE_FILENAME, important_files=IMPORTANT_FILES,
    extra_mandatory_files=[TEST_DIR_FILE],
    artifact_dirnames=parsers.artifact_dirnames, artifact_paths=parsers.artifact_paths,

    parse_always=parsers.parse_always,
    parse_once=parsers.parse_once,
)

parsers.register_important_file = local_store.register_important_file
helpers_store.register_important_file = local_store.register_important_file
is_mandatory_file = local_store.is_mandatory_file
is_cache_file = local_store.is_cache_file
is_important_file = local_store.is_important_file

def _rewrite_settings(settings_dict):
    return settings_dict

# ---
# --- custom store
# ---

def _duplicated_directory(import_key, old_location, new_location):
    logging.warning(f"duplicated results key: {import_key}")
    logging.warning(f"  old: {old_location}")
    logging.warning(f"  new: {new_location}")


def store_parse_directory(results_dir, expe, dirname):
    import_settings = store_simple.parse_settings(dirname)

    def add_to_matrix(results, extra_settings=None):
        pass
    os.environ["MATBENCH_STORE_IGNORE_CACHE"] = "y" # cache mechanism not working
    try:
        logging.info(f"Parsing {dirname} ...")
        extra_settings__results = local_store.parse_directory(add_to_matrix, dirname, import_settings)
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
