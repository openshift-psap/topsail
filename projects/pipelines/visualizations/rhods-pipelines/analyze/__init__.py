import logging

import projects.matrix_benchmarking.visualizations.helpers.analyze as helpers_analyze

from ..store import _rewrite_settings

COMPARISON_KEYS = ["rhoai_version"]

IGNORED_KEYS = ["ocp_version"]

def prepare():
    return helpers_analyze.prepare_regression_data(COMPARISON_KEYS, IGNORED_KEYS, _rewrite_settings)
