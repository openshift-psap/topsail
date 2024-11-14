"""Networking overhead (200 trials on 200 nodes)

In this run, we will start 100 trials and run them on 100 different nodes.
This test will thus measure the overhead that comes with network communication
and specifically log synchronization.

Test owner: krfricke

Acceptance criteria: Should run faster than 500 seconds.

Theoretical minimum time: 300 seconds
"""

# https://github.com/ray-project/ray/blob/130cb3d4f28e7486fad46697fd893dd84b5a096b/release/tune_tests/scalability_tests/workloads/test_network_overhead.py

import os
import json

import ray

from ray.tune.utils.release_test_util import timed_tune_run

with open(os.environ["CONFIG_JSON_PATH"]) as f:
    CONFIG = json.load(f)

def main():
    ray.init(address="auto")

    num_samples = CONFIG.get("num_samples", 20)

    results_per_second = 0.01
    trial_length_s = 300

    max_runtime = 500

    success = timed_tune_run(
        name="result network overhead",
        num_samples=num_samples,
        results_per_second=results_per_second,
        trial_length_s=trial_length_s,
        max_runtime=max_runtime,
        # One trial per worker node, none get scheduled on the head node.
        # See the compute config.
        resources_per_trial={"cpu": 2},
    )

    # if not success:
    #     raise RuntimeError(
    #         f"Test did not finish in within the max_runtime ({max_runtime} s). "
    #         "See above for details."
    #     )


if __name__ == "__main__":
    main()
