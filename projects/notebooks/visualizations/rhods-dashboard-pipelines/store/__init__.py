import pathlib
import logging
import types
import pickle
import fnmatch
import os

import matrix_benchmarking.store as store
import matrix_benchmarking.store.simple as store_simple

import projects.core.visualizations.helpers.store as core_helpers_store

from . import parsers
from . import lts_parser

from ..models import lts as models_lts

CACHE_FILENAME = "cache.pickle"
IMPORTANT_FILES = parsers.IMPORTANT_FILES

local_store = core_helpers_store.BaseStore(
    cache_filename=CACHE_FILENAME, important_files=IMPORTANT_FILES,
    artifact_dirnames=parsers.artifact_dirnames, artifact_paths=parsers.artifact_paths,
    parse_always=parsers.parse_always, parse_once=parsers.parse_once,

    lts_payload_model=models_lts.Payload,
    generate_lts_payload=lts_parser.generate_lts_payload,
)


def _rewrite_settings(settings_dict):
    try: del settings_dict["date"]
    except KeyError: pass

    try: del settings_dict["check_thresholds"]
    except KeyError: pass

    if "repeat" not in settings_dict:
        settings_dict["repeat"] = "1"

    if "live_users" in settings_dict:
        settings_dict["live_users"] = int(settings_dict["live_users"])

    if "users_already_in" in settings_dict:
        settings_dict["users_already_in"] = int(settings_dict["users_already_in"])

    if "user_count" in settings_dict:
        settings_dict["user_count"] = int(settings_dict["user_count"])

    if "launcher" in settings_dict:
        del settings_dict["test_case"]

    del settings_dict["expe"]

    if settings_dict.get("mode") == "notebook_perf":
        for k in ("image", "benchmark_name", "benchmark_repeat", "benchmark_number", "notebook_file_name", "instance_type", "exclude_tags", "test_case"):
            try: del settings_dict[k]
            except KeyError: pass

    return settings_dict

parsers.register_important_file = local_store.register_important_file
build_lts_payloads = local_store.build_lts_payloads
is_mandatory_file = local_store.is_mandatory_file
is_cache_file = local_store.is_cache_file
is_important_file = local_store.is_important_file

# delegate the parsing to the simple_store
store.register_custom_rewrite_settings(_rewrite_settings)
store_simple.register_custom_parse_results(local_store.parse_directory)
