import types

import matrix_benchmarking.store as store
import matrix_benchmarking.store.simple as store_simple

from . import store_prom

def _rewrite_settings(settings_dict):

    if "cakephp-mysql" in settings_dict["host"]:
        settings_dict["host"] = "oauth-proxy"
    if "nginx" in settings_dict["host"]:
        settings_dict["host"] = "nginx"

    del settings_dict["path"]
    del settings_dict["server"]

    return settings_dict

def _parse_directory(fn_add_to_matrix, dirname, import_settings):
    results = types.SimpleNamespace()

    results.metrics = store_prom.extract_metrics(dirname)

    fn_add_to_matrix(results)

    return

def parse_data():
    # delegate the parsing to the simple_store
    store.register_custom_rewrite_settings(_rewrite_settings)
    store_simple.register_custom_parse_results(_parse_directory)

    return store_simple.parse_data()
