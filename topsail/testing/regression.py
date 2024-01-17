import os
import json

import numpy as np
from functools import reduce

from opensearchpy import OpenSearch

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
            client,
            kpi,
            settings=None,
            combine_func=None,
            x_var="_source.@timestamp",
            y_var="_source.value",
            reg_return_codes=regression_return_codes
        ):
        self.client = client
        self.kpi = kpi
        self.settings = settings
        self.combine = combine_func
        self.x_var = x_var
        self.y_var = y_var
        self.reg_ret_codes = reg_return_codes

    def analyze(self, size=10000, timestamp="@timestamp"):

        query = {
            "size": size,
            "sort": {
                f"{timestamp}": {
                    "order": "desc"
                }
            }
        }

        # Restrict the results to specific settings
        if self.settings:
            query["query"] = {
                "bool": {
                    "must": [
                        {"match": {k: v}} for k, v in self.settings.items()
                    ]
                }
            }

        resp = client.search(
            body = query,
            index = self.kpi,
        )

        results = resp["hits"]["hits"]

        if len(results) <= 1:
            return self.reg_ret_codes["UNDEF"]

        curr_result = get_from_path(results[0], self.y_var)
        prev_results = list(map(lambda x: get_from_path(x, self.y_var), results[1:]))
        # Combine the trial results if needed using the provided operator
        if self.combine:
            curr_result = self.combine(curr_result)
            prev_results = list(map(self.combine, prev_results))

        return self.regression_test(curr_result, prev_results)

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

    os_username = os.getenv("OS_USER")
    os_pass = os.getenv("OS_PASS")
    os_endpoint = "opensearch-topsail-opensearch.apps.bm.example.com"
    auth = (os_username, os_pass)


    indices = [
        "notebook_performance_benchmark_min_time",
        "notebook_performance_benchmark_min_max_diff",
        "notebook_gating_test__performance_test",
    ]

    # Start opernsearch client
    client = OpenSearch(
        hosts = [{"host": os_endpoint, "port": 443}],
        http_auth = auth,
        use_ssl=True,
        verify_certs=False,
        ssl_show_warn=False,
    )

    # Create a ZScore indicator to check the 
    # notebook_performance_benchmark_min_max_diff index
    zscore_indicator = ZScoreIndicator(client, indices[1])
    reg_status = zscore_indicator.analyze()
    print(f"ZScoreIndicator -> {reg_status}")

    # Create another ZScore indicator 
    # to check if there is any regression on the
    # notebook_gating_test__performance_test index
    zscore_indicator = ZScoreIndicator(
        client,
        indices[2], # index name
        combine_func=np.mean, # Multiple measured repitions are provided in the data set, call this func to combine them
        x_var="_source.metadata.end", # What we are looking for regression OVER. Ie, time, versions, etc
        y_var="_source.results.benchmark_measures.measures" # The path to the array of trials or scalar measurement
    )
    reg_status = zscore_indicator.analyze(timestamp="metadata.end") # Provide the key for the timestamp so we get most recent test
    print(f"ZScoreIndicator with combine -> {reg_status}")

    # Create a ZScore indicator to check the 
    # notebook_performance_benchmark_min_max_diff index
    # but restrict the regression test to the 2023.1 image name
    zscore_indicator = ZScoreIndicator(client, indices[1], settings={"image_name": "2023.1"})
    reg_status = zscore_indicator.analyze()
    print(f"ZScoreIndicator with image_name=2023.1 -> {reg_status}")
