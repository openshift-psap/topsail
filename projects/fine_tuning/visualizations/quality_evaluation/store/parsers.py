import types
import pathlib
import logging
import yaml
import os
import json
import datetime
import urllib
import uuid

import jsonpath_ng

import matrix_benchmarking.cli_args as cli_args

import projects.core.visualizations.helpers.store as core_helpers_store
import projects.core.visualizations.helpers.store.parsers as core_helpers_store_parsers

register_important_file = None # will be when importing store/__init__.py

K8S_TIME_FMT = "%Y-%m-%dT%H:%M:%SZ"
SHELL_DATE_TIME_FMT = "%a %b %d %H:%M:%S %Z %Y"
ANSIBLE_LOG_DATE_TIME_FMT = "%Y-%m-%d %H:%M:%S"

artifact_dirnames = types.SimpleNamespace()
artifact_dirnames.FINE_TUNING_RUN_QUALITY_EVALUATION_DIR = "*__fine_tuning__run_quality_evaluation"
artifact_paths = types.SimpleNamespace() # will be dynamically populated

IMPORTANT_FILES = [
    ".uuid",
    "config.yaml",

    f"{artifact_dirnames.FINE_TUNING_RUN_QUALITY_EVALUATION_DIR}/src/config_final.json",
    f"{artifact_dirnames.FINE_TUNING_RUN_QUALITY_EVALUATION_DIR}/artifacts/pod.log",
]


def parse_always(results, dirname, import_settings):
    # parsed even when reloading from the cache file
    results.from_local_env = core_helpers_store_parsers.parse_local_env(dirname)

    pass


def parse_once(results, dirname):
    results.test_config = core_helpers_store_parsers.parse_test_config(dirname)
    results.test_uuid = core_helpers_store_parsers.parse_test_uuid(dirname)

    results.quality_evaluation = _parse_quality_evaluation_logs(dirname)
    results.quality_configuration = _parse_quality_configuration(dirname)


@core_helpers_store_parsers.ignore_file_not_found
def _parse_quality_evaluation_logs(dirname):
    quality_evaluation = None
    json_text = []

    with open(register_important_file(dirname, artifact_paths.FINE_TUNING_RUN_QUALITY_EVALUATION_DIR / "artifacts/pod.log")) as f:
        marker_found = False
        for line in f.readlines():
            if marker_found:
                json_text.append(line)
                continue

            if line.startswith("=== JSON output follows ==="):
                marker_found = True

    quality_evaluation = json.loads("".join(json_text))

    return quality_evaluation


def _parse_quality_configuration(dirname):
    quality_configuration = None

    config_file = artifact_paths.FINE_TUNING_RUN_QUALITY_EVALUATION_DIR / "src" / "config_final.json"
    with open(register_important_file(dirname, config_file)) as f:
        quality_configuration = json.load(f)

    return quality_configuration
