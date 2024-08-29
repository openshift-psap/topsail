import logging

import matrix_benchmarking.analyze_lts as analyze_lts

from ..store import _rewrite_settings

COMPARISON_KEYS = ["rhoai_version"]

IGNORED_KEYS = ["ocp_version"]

def prepare():
    return analyze_lts.prepare_regression_data(COMPARISON_KEYS, IGNORED_KEYS, _rewrite_settings)
