import pandas as pd

import logging

import matrix_benchmarking.common as common
from ..store import _rewrite_settings

COMPARISON_KEY = "rhoai_version"

_IGNORED_KEYS = ["runtime_image", "ocp_version"]

def run():
    logging.info("Running the regression analyses ...")

    data = []
    for ref_entry in common.Matrix.all_records():
        lts_payload = ref_entry.results.lts

        if not hasattr(lts_payload, "kpis"):
            logging.warning("No KPIs available ...")
            continue

        kpis = lts_payload.kpis

        current_row = dict(ref=ref_entry)

        for entry in common.LTS_Matrix.similar_records(ref_entry.results.lts.metadata.settings,
                                                       ignore_keys=([COMPARISON_KEY] + _IGNORED_KEYS),
                                                       rewrite_settings=_rewrite_settings,
                                                       gathered=True):
            current_row[entry.settings.rhoai_version] = entry

        data.append(current_row)

    return pd.DataFrame(data)
