import pathlib
import logging
import types
import pickle
import fnmatch
import os

import matrix_benchmarking.store as store
import matrix_benchmarking.store.simple as store_simple

from . import parsers
from ..models import lts as models_lts
from . import lts_parser

CACHE_FILENAME = "cache.pickle"

IMPORTANT_FILES = parsers.IMPORTANT_FILES

PARSER_VERSION = parsers.PARSER_VERSION
ARTIFACTS_VERSION = parsers.ARTIFACTS_VERSION

store.register_lts_schema(models_lts.Payload)

def is_mandatory_file(filename):
    return filename.name in ("settings", "exit_code", "config.yaml") or filename.name.startswith("settings.")


def is_important_file(filename):
    if str(filename) in IMPORTANT_FILES:
        return True

    for important_file in IMPORTANT_FILES:
        if "*" not in important_file: continue

        if fnmatch.filter([str(filename)], important_file):
            return True

    return False


def is_cache_file(filename):
    return filename.name == CACHE_FILENAME


def register_important_file(base_dirname, filename):
    if not is_important_file(filename):
        logging.warning(f"File '{filename}' not part of the important file list :/")
        if pathlib.Path(filename).is_absolute():
            logging.warning(f"File '{filename}' is an absolute path. Should be relative to {base_dirname}.")
    return base_dirname / filename

parsers.register_important_file = register_important_file


def _rewrite_settings(settings_dict):
    return settings_dict


def load_cache(dirname):
    try:
        with open(dirname / CACHE_FILENAME, "rb") as f:
            results = pickle.load(f)

        cache_version = getattr(results, "parser_version", None)
        if cache_version != PARSER_VERSION:
            raise ValueError(cache_version)

    except ValueError as e:
        cache_version = e.args[0]
        if not cache_version:
            logging.warning(f"Cache file '{dirname / CACHE_FILENAME}' does not have a version, ignoring.")
        else:
            logging.warning(f"Cache file '{dirname / CACHE_FILENAME}' version '{cache_version}' does not match the parser version '{PARSER_VERSION}', ignoring.")

        results = None

    return results


def _parse_directory(fn_add_to_matrix, dirname, import_settings):
    ignore_cache = os.environ.get("MATBENCH_STORE_IGNORE_CACHE", False) in ("yes", "y", "true", "True")
    if not ignore_cache:
        try:
            results = load_cache(dirname)
        except FileNotFoundError:
            results = None # Cache file doesn't exit, ignore and parse the artifacts
    else:
        logging.info("MATBENCH_STORE_IGNORE_CACHE is set, not processing the cache file.")
        results = None

    if results:
        parsers._parse_always(results, dirname, import_settings)

        fn_add_to_matrix(results)

        return

    results = types.SimpleNamespace()

    results.parser_version = PARSER_VERSION
    results.artifacts_version = ARTIFACTS_VERSION

    if results.artifacts_version != ARTIFACTS_VERSION:
        if not results.artifacts_version:
            logging.warning("Artifacts does not have a version...")
        else:
            logging.warning(f"Artifacts version '{results.artifacts_version}' does not match the parser version '{ARTIFACTS_VERSION}' ...")

    parsers._parse_always(results, dirname, import_settings)
    parsers._parse_once(results, dirname)

    lts_results = lts_parser.generate_lts_results(results)
    results.lts = lts_parser.generate_lts_payload(results, lts_results, import_settings, must_validate=False)

    fn_add_to_matrix(results)

    with open(dirname / CACHE_FILENAME, "wb") as f:
        get_config = results.test_config.get
        results.test_config.get = None

        pickle.dump(results, f)

        results.test_config.get = get_config

    print("parsing done :)")


def parse_data():
    # delegate the parsing to the simple_store
    store.register_custom_rewrite_settings(_rewrite_settings)
    store_simple.register_custom_parse_results(_parse_directory)

    from . import lts
    store_simple.register_custom_lts_parse_results(lts._parse_lts_dir)
    store_simple.register_custom_build_lts_payloads(lts.build_lts_payloads)

    return store_simple.parse_data()


def build_lts_payloads():
    return store_simple.build_lts_payloads()
