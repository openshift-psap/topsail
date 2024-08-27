import pathlib
import logging
import types
import os
import json

import matrix_benchmarking.store as store
import matrix_benchmarking.store.simple as store_simple

import projects.core.visualizations.helpers.store as core_helpers_store
import projects.core.visualizations.helpers.store as core_helpers

from . import parsers
from . import lts_parser
from ..models import lts as models_lts
from ..models import kpi as models_kpi

CACHE_FILENAME = "cache.pickle"
IMPORTANT_FILES = parsers.IMPORTANT_FILES

class KserverLlmStore(core_helpers_store.BaseStore):
    def prepare_for_pickle(self, results):
        results.llm_load_test_config.get = None

    def prepare_after_pickle(self, results):
        results.llm_load_test_config.get = core_helpers.get_yaml_get_key(
            results.llm_load_test_config.name,
            results.llm_load_test_config.yaml_file
        )

local_store = KserverLlmStore(
    cache_filename=CACHE_FILENAME, important_files=IMPORTANT_FILES,
    artifact_dirnames=parsers.artifact_dirnames, artifact_paths=parsers.artifact_paths,
    parse_always=parsers.parse_always, parse_once=parsers.parse_once,

    lts_payload_model=models_lts.Payload,
    generate_lts_payload=lts_parser.generate_lts_payload,

    models_kpis=models_kpi.KPIs,
    get_kpi_labels=lts_parser.get_kpi_labels,
)

parsers.register_important_file = local_store.register_important_file
build_lts_payloads = local_store.build_lts_payloads
is_mandatory_file = local_store.is_mandatory_file
is_cache_file = local_store.is_cache_file
is_important_file = local_store.is_important_file


def rewrite_runtime_image(runtime_image):
    if not runtime_image: return None

    if "/" in runtime_image:
        return runtime_image.split("/")[-1].split("@")[0]
    else:
        return "tgis-caikit"

def _rewrite_settings(settings_dict):
    settings_dict.pop("run_id", None)
    settings_dict.pop("urls", None)
    settings_dict.pop("test_path", None)

    runtime_image = settings_dict.get("runtime_image", None)

    if runtime_image:
        settings_dict["runtime"] = rewrite_runtime_image(runtime_image)

    return settings_dict

# delegate the parsing to the simple_store
store.register_custom_rewrite_settings(_rewrite_settings)
store_simple.register_custom_parse_results(local_store.parse_directory)
