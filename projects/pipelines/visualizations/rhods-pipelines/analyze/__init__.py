import logging

import projects.core.visualizations.helpers.analyze as core_helpers_analyze

from ..store import _rewrite_settings

COMPARISON_KEYS = ["rhoai_version"]

IGNORED_KEYS = ["ocp_version"]

def prepare():
    return core_helpers_analyze.prepare_regression_data(COMPARISON_KEYS, IGNORED_KEYS, _rewrite_settings)
