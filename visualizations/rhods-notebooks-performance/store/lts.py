import types
import datetime
import logging
import pytz

import matrix_benchmarking.common as common

from ..import models

def build_lts_payloads():

    for entry in common.Matrix.processed_map.values():
        results = entry.results

        start_time = results.start_time
        end_time = results.end_time

        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=pytz.UTC)
        if end_time.tzinfo is None:
            end_time = end_time.replace(tzinfo=pytz.UTC)

        lts_payload = {
            "$schema": "urn:rhods-notebooks-perf:1.0.0",
            "metadata": {
                "start": start_time,
                "end": end_time,
                "presets": results.test_config.get("ci_presets.names") or ["no_preset_defined"],
                "config": results.test_config.yaml_file,
                "rhods_version": results.rhods_info.version,
                "ocp_version": results.sutest_ocp_version,
                "settings": entry.settings.__dict__,
                "test": results.test_config.get('tests.notebooks.identifier') or 'unknown'
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
