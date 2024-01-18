import os
import json

from datetime import datetime

import numpy as np
from functools import reduce

regression_return_codes = {
    "POS_REG": 1,
    "NEG_REG": -1,
    "NONE": 0,
    "UNDEF": 2,
}

def get_from_path(d, path):
    return reduce(dict.get, path.split("."), d)

class RegressionIndicator:

    def __init__(
            self,
            payloads,
            combine_func=None,
            x_var="_source.@timestamp",
            y_var="_source.value",
            reg_return_codes=regression_return_codes,
            return_aggregator_func=lambda x, y: x or y,
        ):
        self.payloads = payloads
        self.combine = combine_func
        self.x_var = x_var
        self.y_var = y_var
        self.reg_ret_codes = reg_return_codes
        self.ret_agg_func = return_aggregator_func

    def analyze(self, timestamp="@timestamp", kpi=None):

        if len(self.payloads) <= 1:
            return regression_return_codes["UNDEF"]

        self.payloads.sort(key=lambda pl: datetime.fromisoformat(get_from_path(pl, "metadata.end")).astimezone())
        curr_result = self.payloads[0]
        prev_results = self.payloads[1:]

        kpis = [k for k, v in curr_result["kpis"].items()] if kpi is None else [kpi]

        regression_results = []
        for kpi_name in kpis:
            print(kpi_name)
            curr_value = curr_result["kpis"][kpi_name]["value"]
            prev_values = list(map(lambda x: x["kpis"][kpi_name]["value"], prev_results))
            regression_results.append(self.regression_test(curr_value, prev_values))

        print(regression_results)
        return reduce(self.ret_agg_func, regression_results, 0)

    def regression_test(self, curr_result, prev_result):
        return self.reg_test_codes["NONE"]



class ZScoreIndicator(RegressionIndicator):
    """
    Example regression indicator that uses the Z score as a metric
    to determine if the recent test was an outlier
    """
    def __init__(self, *args, threshold=3, **kwargs):
        super().__init__(*args, **kwargs)
        self.threshold = threshold

    def regression_test(self, curr_result, prev_results):
        """
        Determine if the curr_result is more/less than threshold
        standard deviations away from the previous_results
        """
        mean = np.mean(prev_results)
        std = np.std(prev_results)
        z_score = (curr_result - mean) / std
        if abs(z_score) > self.threshold:
            if z_score < 0:
                return -1
            else:
                return 1
        else:
            return 0

class PolynomialRegressionIndicator(RegressionIndicator):
    """
    Placeholder for polynomial regression that we could implement
    somewhere in the pipeline
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def regression_test(self, curr_result, prev_results):
        return 0


if __name__ == '__main__':

    artifacts_dir = os.getenv("ARTIFACTS_DIR")
    json_payloads = []
    for filename in os.listdir(artifacts_dir):
        with open(os.path.join(artifacts_dir, filename)) as raw_json_f:
            if filename[-5:] == ".json":
                json_payloads.append(json.load(raw_json_f))

    # Create a ZScore indicator to check the 
    # notebook_performance_benchmark_min_max_diff index
    zscore_indicator = ZScoreIndicator(json_payloads)
    reg_status = zscore_indicator.analyze()
    print(f"ZScoreIndicator -> {reg_status}")
