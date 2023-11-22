import pathlib
import logging
import types
import pickle
import fnmatch
import os

import matrix_benchmarking.store as store
import matrix_benchmarking.store.simple as store_simple

from . import parsers
from . import lts

CACHE_FILENAME = "cache.pickle"

IMPORTANT_FILES = parsers.IMPORTANT_FILES

from ..models import lts as models_lts

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


def resolve_artifact_dirnames(dirname, artifact_dirnames):
    artifact_paths = types.SimpleNamespace()
    for artifact_dirname, unresolved_dirname in artifact_dirnames.__dict__.items():
        direct_resolution = dirname / unresolved_dirname
        resolutions = list(dirname.glob(unresolved_dirname))
        resolved_dir = None

        if direct_resolution.exists():
            # all good
            resolved_dir = direct_resolution
        elif not resolutions:
            logging.warning(f"Cannot resolve {artifact_dirname} glob '{unresolved_dirname}' in '{dirname}'")
        else:
            if len(resolutions) > 1:
                logging.error(f"Could multiple resolutions for {artifact_dirname} glob '{unresolved_dirname}' in '{dirname}': {resolutions}. Taking the first one")

            resolved_dir = resolutions[0]

        if resolved_dir:
            resolved_dir = resolved_dir.relative_to(dirname)

        artifact_paths.__dict__[artifact_dirname] = resolved_dir

    return artifact_paths


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
    with open(dirname / CACHE_FILENAME, "rb") as f:
        return pickle.load(f)


def _parse_directory(fn_add_to_matrix, dirname, import_settings):
    parsers.artifact_paths = resolve_artifact_dirnames(dirname, parsers.artifact_dirnames)

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

    parsers._parse_always(results, dirname, import_settings)
    parsers._parse_once(results, dirname)

    fn_add_to_matrix(results)

    with open(dirname / CACHE_FILENAME, "wb") as f:
        get_config = results.test_config.get
        results.test_config.get = None

        pickle.dump(results, f)

        results.test_config.get = get_config

    logging.info("parsing done :)")


def parse_data():
    # delegate the parsing to the simple_store
    store.register_custom_rewrite_settings(_rewrite_settings)
    store_simple.register_custom_parse_results(_parse_directory)

    store_simple.register_custom_lts_parse_results(lts._parse_lts_dir)
    store_simple.register_custom_build_lts_payloads(lts.build_lts_payloads)

    return store_simple.parse_data()


def build_lts_payloads():
    return store_simple.build_lts_payloads()
