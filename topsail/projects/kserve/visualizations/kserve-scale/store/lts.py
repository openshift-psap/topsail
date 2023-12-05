import logging

import matrix_benchmarking.common as common

from .. import models
from ..models import lts as models_lts

def build_lts_payloads():
    for entry in common.Matrix.processed_map.values():
        results = entry.results

        start_time = results.test_start_end_time.start
        end_time = results.test_start_end_time.end

        # To know the available metrics:
        # _=[print(m) for m in results.metrics["sutest"].keys()]

        lts_payload = {
            "metadata": {
                "start": start_time,
                "end": end_time,
                "presets": results.test_config.get("ci_presets.names") or ["no_preset_defined"],
                "config": results.test_config.yaml_file,
                "ocp_version": results.sutest_ocp_version,
                "settings": entry.settings.__dict__,
            },
            "results": {
                "fake_results": True,

                "metrics": _gather_prom_metrics(results.metrics["sutest"], models.lts.Metrics),
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


def _gather_prom_metrics(metrics, model) -> dict:
    data = {metric_name: metrics[metric_name]
            for metric_name in model.schema()["properties"].keys()}

    return model(**data)
