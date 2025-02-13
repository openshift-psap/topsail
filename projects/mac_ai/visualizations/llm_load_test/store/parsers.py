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

import matrix_benchmarking.cli_args as cli_args

import projects.matrix_benchmarking.visualizations.helpers.store as helpers_store
import projects.matrix_benchmarking.visualizations.helpers.store.parsers as helpers_store_parsers

from . import lts_parser

register_important_file = None # will be when importing store/__init__.py

artifact_dirnames = types.SimpleNamespace()
artifact_dirnames.LLM_LOAD_TEST_RUN_DIR = "*__llm_load_test__run"

artifact_paths = types.SimpleNamespace() # will be dynamically populated

IMPORTANT_FILES = [
    "config.yaml",
    ".uuid",

    f"{artifact_dirnames.LLM_LOAD_TEST_RUN_DIR}/output/output.json",
    f"{artifact_dirnames.LLM_LOAD_TEST_RUN_DIR}/src/llm_load_test.config.yaml",

]


def parse_always(results, dirname, import_settings):
    # parsed even when reloading from the cache file

    results.from_local_env = helpers_store_parsers.parse_local_env(dirname)


def parse_once(results, dirname):
    results.test_config = helpers_store_parsers.parse_test_config(dirname)

    results.test_uuid = helpers_store_parsers.parse_test_uuid(dirname)

    results.llm_load_test_config = _parse_llm_load_test_config(dirname)
    results.llm_load_test_output = _parse_llm_load_test_output(dirname)

    results.test_start_end = _parse_test_start_end(dirname, results.llm_load_test_output)


@helpers_store_parsers.ignore_file_not_found
def _parse_llm_load_test_output(dirname):
    llm_output_file = dirname / artifact_paths.LLM_LOAD_TEST_RUN_DIR / "output" / "output.json"
    register_important_file(dirname, llm_output_file.relative_to(dirname))

    with open(llm_output_file) as f:
        llm_load_test_output = json.load(f)

    return llm_load_test_output


@helpers_store_parsers.ignore_file_not_found
def _parse_llm_load_test_config(dirname):
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
