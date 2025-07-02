import matrix_benchmarking.store as store
import matrix_benchmarking.store.simple as store_simple

import projects.matrix_benchmarking.visualizations.helpers.store as helpers_store

from . import parsers

CACHE_FILENAME = "cache.pickle"
IMPORTANT_FILES = parsers.IMPORTANT_FILES


class KserverBenchamrkStore(helpers_store.BaseStore):
    def prepare_for_pickle(self, results):
        if results.test_config:
            results.test_config.get = None

    def prepare_after_pickle(self, results):
        if results.test_config:
            results.test_config.get = helpers_store.get_yaml_get_key(
                results.test_config.name,
                results.test_config.yaml_file
            )


local_store = KserverBenchamrkStore(
    cache_filename=CACHE_FILENAME, important_files=IMPORTANT_FILES,
    artifact_dirnames=parsers.artifact_dirnames, artifact_paths=parsers.artifact_paths,
    parse_always=parsers.parse_always, parse_once=parsers.parse_once,
)

parsers.register_important_file = local_store.register_important_file
build_lts_payloads = local_store.build_lts_payloads
is_mandatory_file = local_store.is_mandatory_file
is_cache_file = local_store.is_cache_file
is_important_file = local_store.is_important_file


def _rewrite_settings(settings_dict, results=None, is_lts=None):

    if results is None:
        # when trying to find simular results
        # (matrix_benchmarking.common.similar_records), the results
        # aren't available. Cannot rewrite the settings without it.
        return settings_dict

    test_platform = settings_dict.pop("test.platform", results.test_config.get("test.platform"))
    if "platform" not in settings_dict:
        settings_dict["platform"] = test_platform

    test_benchmark = settings_dict.pop("test.benchmark", results.test_config.get("test.benchmark"))
    if "benchmark" not in settings_dict:
        settings_dict["benchmark"] = test_benchmark

    return settings_dict


# delegate the parsing to the simple_store
store.register_custom_rewrite_settings(_rewrite_settings)
store_simple.register_custom_parse_results(local_store.parse_directory)
