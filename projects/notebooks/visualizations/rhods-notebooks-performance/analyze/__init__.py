import json
import logging
import numpy as np

from copy import deepcopy

import matrix_benchmarking.common as common
import matrix_benchmarking.regression as regression
import matrix_benchmarking.regression.zscore as zscore

def run():

    logging.info(f"Received {common.LTS_Matrix.count_records()} historic LTS entries")
    lts_entries = []
    # Take the first result if they were gathered
    for entry in common.LTS_Matrix.all_records():
        if entry.results and type(entry.results) is list:
            entry.results = entry.results[0]
            lts_entries.append(entry)
        else:
            lts_entries.append(entry)

    logging.info(f"Received {common.Matrix.count_records()} new entries")

    number_of_failures = 0
    settings_to_check = ["version", "repeat"]
    for entry in common.Matrix.all_records():
        regression_results_dest = entry.location / "regression.json"
        regression_results = {}
        for check_setting in settings_to_check:
            controlled_settings = entry.get_settings()

            try:
                controlled_settings.pop(check_setting)
            except KeyError:
                logging.warning(f"Couldn't find {check_setting} setting for entry={entry.location}, skipping...")
                continue

            controlled_lts_entries = list(
                filter(
                    lambda x: regression.dict_part_eq(controlled_settings, x.get_settings()),
                    lts_entries
                )
            )
            zscore_ind = zscore.ZScoreIndicator(entry, controlled_lts_entries)
            regression_results[check_setting] = zscore_ind.analyze()
            number_of_failures += sum(map(lambda x: x["regression"]["status"], regression_results[check_setting]))

        logging.info(f"Saving the regression results in {regression_results_dest}")
        with open(regression_results_dest, "w") as f:
            json.dump(regression_results, f, indent=4)
            print("", file=f)

    return number_of_failures
