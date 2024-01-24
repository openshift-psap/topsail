import json
import logging
import numpy as np

from copy import deepcopy

import matrix_benchmarking.common as common
import matrix_benchmarking.regression as regression

def run():

    logging.info(f"Received {common.LTS_Matrix.count_records()} historic LTS entries")
    lts_entries_raw = list(common.LTS_Matrix.all_records())
    # Temporarily skip the gathered results
    lts_entries = list(filter(lambda entry: type(entry.results) is not list, lts_entries_raw))

    logging.info(f"Received {common.Matrix.count_records()} new entries")
    new_entries = list(common.Matrix.all_records())

    number_of_failures = 0
    for entry in common.Matrix.all_records():
        regression_results_dest = entry.location / "regression.json"

        # Check for regression over the image
        zscore = regression.ZScoreIndicator(
            entry,
            lts_entries,
            settings_filter={"image": "tensorflow:2023.1"},
            combine_funcs={"notebook_performance_benchmark_time": np.mean}
        )

        logging.info(f"Saving the regression results in {regression_results_dest}")
        regression_results = zscore.analyze()
        with open(regression_results_dest, "w") as f:
            json.dump(regression_results, f, indent=4)
            print("", file=f)
        number_of_failures += sum(map(lambda x: x["regression"]["status"], regression_results))

    return number_of_failures
