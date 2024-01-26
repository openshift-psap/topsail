import json
import logging
import numpy as np

from copy import deepcopy

import matrix_benchmarking.common as common
import matrix_benchmarking.regression as regression

def run():

    logging.info(f"Received {common.LTS_Matrix.count_records()} historic LTS entries")
    lts_entries = []
    for entry in common.LTS_Matrix.all_records():
        if entry.results and type(entry.results) is list:
            entry.results = entry.results[0]
            lts_entries.append(entry)
        else:
            lts_entries.append(entry)

    logging.info(f"Received {common.Matrix.count_records()} new entries")

    number_of_failures = 0
    for entry in common.Matrix.all_records():
        regression_results_dest = entry.location / "regression.json"
        regression_results = []
        controlled_settings = entry.get_settings()
        controlled_settings.pop("repeat") # Looking for regressions over the version, repeat is a placeholder
        controlled_lts_entries = list(
            filter(
                lambda x: regression.dict_part_eq(controlled_settings, x.get_settings()),
                lts_entries
            )
        )
        zscore = regression.ZScoreIndicator(entry, controlled_lts_entries)
        regression_results = zscore.analyze()
        number_of_failures += sum(map(lambda x: x["regression"]["status"], regression_results))

        logging.info(f"Saving the regression results in {regression_results_dest}")
        with open(regression_results_dest, "w") as f:
            json.dump(regression_results, f, indent=4)
            print("", file=f)

    return number_of_failures
