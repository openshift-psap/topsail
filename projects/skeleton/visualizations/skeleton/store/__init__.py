import pathlib
import logging
import types
import pickle
import fnmatch
import os

import matrix_benchmarking.store as store
import matrix_benchmarking.store.simple as store_simple

import projects.matrix_benchmarking.visualizations.helpers.store as helpers_store

from . import parsers
from . import lts_parser
from ..models import kpi as models_kpi
from ..models import lts as models_lts

CACHE_FILENAME = "cache.pickle"
IMPORTANT_FILES = parsers.IMPORTANT_FILES

local_store = helpers_store.BaseStore(
    cache_filename=CACHE_FILENAME, important_files=IMPORTANT_FILES,
    artifact_dirnames=parsers.artifact_dirnames, artifact_paths=parsers.artifact_paths,
    parse_always=parsers.parse_always, parse_once=parsers.parse_once,

    lts_payload_model=models_lts.Payload,
    generate_lts_payload=lts_parser.generate_lts_payload,

    models_kpis=models_kpi.KPIs,
    get_kpi_labels=lts_parser.get_kpi_labels,
)


def _rewrite_settings(settings_dict):
    return settings_dict

build_lts_payloads = local_store.build_lts_payloads
parsers.register_important_file = local_store.register_important_file
# delegate the parsing to the simple_store
store.register_custom_rewrite_settings(_rewrite_settings)
store_simple.register_custom_parse_results(local_store.parse_directory)
