import logging

import projects.core.visualizations.helpers.analyze as core_helpers_analyze

from ..store import _rewrite_settings

# the setting (kpi labels) keys against which the historical regression should be performed
COMPARISON_KEYS = ["rhoai_version"]

# the setting (kpi labels) keys that should be ignored when searching for historical results
IGNORED_KEYS = ["runtime_image", "ocp_version"]

# the setting (kpi labels) keys *prefered* for sorting the entries in the regression report
SORTING_KEYS = ["model_name", "virtual_users"]

IGNORED_ENTRIES = {
    "virtual_users": [4, 8, 32, 128]
}

def prepare():
    return core_helpers_analyze.prepare_regression_data(COMPARISON_KEYS, IGNORED_KEYS, _rewrite_settings,
                                                        sorting_keys=SORTING_KEYS,
                                                        ignored_entries=IGNORED_ENTRIES)
