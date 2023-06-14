import types
import datetime
import logging

import matrix_benchmarking.common as common

from ..import models

def build_lts_payloads():

    for entry in common.Matrix.processed_map.values():
        results = entry.results

        start_time = results.start_time
        end_time = results.end_time

        lts_payload = {
            "metadata": {
                "start": start_time,
                "end": end_time,
                "presets": results.test_config.get("ci_presets.names") or ["no_preset_defined"],
                "config": results.test_config.yaml_file,
                "rhods_version": results.rhods_info.version,
                "ocp_version": results.sutest_ocp_version,
                "settings": entry.settings.__dict__,
            },
            "results": {
                "benchmark_measures": results.notebook_benchmark,
            },
        }

        try:
            models.lts.Payload.parse_obj(lts_payload)
        except Exception as e:
            logging.error("internal-error: Failed to validate the LTS payload against the model", e)
            raise e

        yield lts_payload, start_time, end_time


def _parse_lts_dir(add_to_matrix, dirname, import_settings):
    pass
