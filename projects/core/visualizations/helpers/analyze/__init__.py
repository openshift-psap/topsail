import logging

import pandas as pd

import matrix_benchmarking.common as common

def prepare_regression_data(comparison_keys, ignored_keys, rewrite_settings, sorting_keys=[]):
    logging.info("Preparing the regression analyses records ...")

    data = []
    for ref_entry in common.Matrix.all_records():
        lts_payload = ref_entry.results.lts

        if not hasattr(lts_payload, "kpis"):
            logging.warning("No KPIs available ...")
            continue

        kpis = lts_payload.kpis

        def get_name(settings):
            return getattr(settings, comparison_keys[0]) if len(comparison_keys) == 1 \
                else "|".join([f"{k}={settings.__dict__[k]}" for k in comparison_keys])

        ref_name = get_name(ref_entry.results.lts.metadata.settings)

        current_row = {
            ref_name: ref_entry,
            "ref": ref_name,
        }

        for entry in common.LTS_Matrix.similar_records(ref_entry.results.lts.metadata.settings,
                                                       ignore_keys=(comparison_keys + ignored_keys),
                                                       rewrite_settings=rewrite_settings,
                                                       gathered=True):

            name = get_name(entry.settings)
            if name == ref_name: continue
            current_row[name] = entry

        data.append(current_row)

    return pd.DataFrame(data), comparison_keys, ignored_keys, sorting_keys
