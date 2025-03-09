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
import matrix_benchmarking.store.prom_db as store_prom_db

import projects.matrix_benchmarking.visualizations.helpers.store as helpers_store
import projects.matrix_benchmarking.visualizations.helpers.store.parsers as helpers_store_parsers

from . import prom as workload_prom

register_important_file = None # will be when importing store/__init__.py

K8S_TIME_FMT = "%Y-%m-%dT%H:%M:%SZ"
SHELL_DATE_TIME_FMT = "%a %b %d %H:%M:%S %Z %Y"
ANSIBLE_LOG_DATE_TIME_FMT = "%Y-%m-%d %H:%M:%S"

artifact_dirnames = types.SimpleNamespace()
artifact_dirnames.CLUSTER_CAPTURE_ENV_DIR = "*__cluster__capture_environment"
artifact_dirnames.CLUSTER_DUMP_PROM_DB_DIR = "*__cluster__dump_prometheus_db"
artifact_paths = types.SimpleNamespace() # will be dynamically populated

IMPORTANT_FILES = [
    "config.yaml",
    f"{artifact_dirnames.CLUSTER_DUMP_PROM_DB_DIR}/prometheus.t*",
    f"{artifact_dirnames.CLUSTER_CAPTURE_ENV_DIR}/_ansible.log",
    f"{artifact_dirnames.CLUSTER_CAPTURE_ENV_DIR}/nodes.json",
    f"{artifact_dirnames.CLUSTER_CAPTURE_ENV_DIR}/ocp_version.yml"
]


def parse_always(results, dirname, import_settings):
    # parsed even when reloading from the cache file
    results.from_local_env = helpers_store_parsers.parse_local_env(dirname)

    pass


def parse_once(results, dirname):
    results.test_config = helpers_store_parsers.parse_test_config(dirname)
    results.test_uuid = helpers_store_parsers.parse_test_uuid(dirname)

    capture_state_dir = artifact_paths.CLUSTER_CAPTURE_ENV_DIR
    results.ocp_version = helpers_store_parsers.parse_ocp_version(dirname, capture_state_dir)
    results.from_env = helpers_store_parsers.parse_env(dirname, results.test_config, capture_state_dir)
    results.nodes_info = helpers_store_parsers.parse_nodes_info(dirname, capture_state_dir)
    results.cluster_info = helpers_store_parsers.extract_cluster_info(results.nodes_info)

    results.metrics = _extract_metrics(dirname)

    results.test_start_end_time = _parse_start_end_time(dirname)


def _extract_metrics(dirname):
    if not artifact_paths.CLUSTER_DUMP_PROM_DB_DIR:
        return None

    db_files = {
        "sutest": (str(artifact_paths.CLUSTER_DUMP_PROM_DB_DIR / "prometheus.t*"), workload_prom.get_sutest_metrics()),
    }

    return helpers_store_parsers.extract_metrics(dirname, db_files)


@helpers_store_parsers.ignore_file_not_found
def _parse_start_end_time(dirname):
    ANSIBLE_LOG_TIME_FMT = '%Y-%m-%d %H:%M:%S'

    test_start_end_time = types.SimpleNamespace()
    test_start_end_time.start = None
    test_start_end_time.end = None

    with open(register_important_file(dirname, artifact_paths.CLUSTER_CAPTURE_ENV_DIR / "_ansible.log")) as f:
        for line in f.readlines():
            time_str = line.partition(",")[0] # ignore the MS
            if test_start_end_time.start is None:
                test_start_end_time.start = datetime.datetime.strptime(time_str, ANSIBLE_LOG_TIME_FMT)
        if test_start_end_time.start is None:
            raise ValueError("Ansible log file is empty :/")

        test_start_end_time.end = datetime.datetime.strptime(time_str, ANSIBLE_LOG_TIME_FMT)

    return test_start_end_time
