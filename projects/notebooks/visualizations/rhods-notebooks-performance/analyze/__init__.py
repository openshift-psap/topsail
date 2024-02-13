import json
import logging
import numpy as np

from typing import List

import matrix_benchmarking.common as common
import matrix_benchmarking.regression as regression
import matrix_benchmarking.regression.hunter as hunter

def run():

    logging.info(f"Received {common.LTS_Matrix.count_records()} historic LTS entries")
    lts_entries = list(common.LTS_Matrix.all_records())

    logging.info(f"Received {common.Matrix.count_records()} new entries")

    number_of_failures = 0
    settings_to_check = ["rhoai_version", "ocp_version"]
    for entry in common.Matrix.all_records():
        regression_results_dest = entry.location / "regression.json"
        regression_results: List[models.RegressionResult] = []
        for check_setting in settings_to_check:
            # This will likely need to be updated with the settings that must be equal between entries
            # for them to be considered similar enough for comparison against LTS entries
            controlled_settings = {setting: dict(entry.get_settings())[setting] for setting in ["ocp_version"]}

            controlled_lts_entries = list(
                filter(
                    lambda x: regression.dict_part_eq(controlled_settings, dict(x.get_settings())),
                    lts_entries
                )
            )
            if len(controlled_lts_entries) < 1:
                logging.warning("No LTS entries left after filtering")
            hunter_ind = hunter.HunterWrapperIndicator(entry, controlled_lts_entries, check_setting)
            results: List[models.RegressionResult] = hunter_ind.analyze()
            # Add back the setting that we are testing since we handled the filtering manually
            for result in results:
                result.metric = check_setting
                regression_results.append(result)

            number_of_failures += sum([x.status for x in results])

        logging.info(f"Saving the regression results in {regression_results_dest}")
        with open(regression_results_dest, "w") as f:
            json_results = [dict(m) for m in regression_results]
            json.dump(json_results, f, indent=4)
            print("", file=f)

    return number_of_failures
