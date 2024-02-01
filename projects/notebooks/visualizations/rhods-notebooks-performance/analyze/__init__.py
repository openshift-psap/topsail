import json
import logging

import matrix_benchmarking.common as common


def run():
    logging.info(f"Received {common.Matrix.count_records()} new entries")
    for entry in common.Matrix.all_records():
        pass

    logging.info(f"Received {common.LTS_Matrix.count_records()} historic LTS entries")
    for lts_entry in common.LTS_Matrix.all_records(): pass

    number_of_failures = 0

    return number_of_failures
