import pathlib
import logging
import types
import os
import json

import matrix_benchmarking.store as store
import matrix_benchmarking.store.simple as store_simple

import projects.matrix_benchmarking.visualizations.helpers.store as helpers_store

from . import parsers
from . import lts_parser
from ..models import lts as models_lts
from ..models import kpi as models_kpi

CACHE_FILENAME = "cache.pickle"
IMPORTANT_FILES = parsers.IMPORTANT_FILES

class KserverLlmStore(helpers_store.BaseStore):
    def prepare_for_pickle(self, results):
        if results.llm_load_test_config:
            results.llm_load_test_config.get = None

    def prepare_after_pickle(self, results):
        if results.llm_load_test_config:
            results.llm_load_test_config.get = helpers_store.get_yaml_get_key(
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

def _rewrite_settings(settings_dict, results=None, is_lts=None):
    if is_lts:
        if settings_dict["model_name"] == "llama3.2":
            settings_dict["model_name"] = "llama3.2/llama3.2"

        return settings_dict

    if results is None:
        # when trying to find simular results
        # (matrix_benchmarking.common.similar_records), the results
        # aren't available. Cannot rewrite the settings without it.
        return settings_dict

    model_name = settings_dict.pop("test.model.name", results.test_config.get("test.model.name"))
    if "model_name" not in settings_dict:
        settings_dict["model_name"] = model_name

    test_platform = settings_dict.pop("test.platform", results.test_config.get("test.platform"))
    if "platform" not in settings_dict:
        settings_dict["platform"] = test_platform

    for k in list(settings_dict.keys()):
        _, found, param = k.partition("test.llm_load_test.args.")
        if found: settings_dict[param] = settings_dict.pop(k)

    if "model_name" not in settings_dict:
        settings_dict["model_name"] = results.lts.metadata.settings.model_name

    return settings_dict

# delegate the parsing to the simple_store
store.register_custom_rewrite_settings(_rewrite_settings)
store_simple.register_custom_parse_results(local_store.parse_directory)
