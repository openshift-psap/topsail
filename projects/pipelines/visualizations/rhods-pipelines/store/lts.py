from typing import Union

import matrix_benchmarking.common as common

from . import prom
from ..models import lts as models_lts

def build_lts_payloads():
    prom.register(only_initialize=True) # this call populates the 'lts_metrics' structure

    for entry in common.Matrix.processed_map.values():
        results = entry.results

        lts_metadata = models_lts.Metadata(
            start = results.tester_job.creation_time,
            end = results.tester_job.completion_time,
            presets = results.test_config["get"]("ci_presets.names") or ["no_preset_defined"],
            settings = entry.settings.__dict__,
            ocp_version = results.sutest_ocp_version,
            rhods_version = results.rhods_info.full_version,
            user_count = results.user_count,
            config = results.test_config["yaml_file"],
        )

        lts_results = models_lts.Results(
            metrics = models_lts.Metrics(
                sutest = _gather_prom_metrics(entry.results.metrics.sutest, models_lts.SutestMetrics),
            ),
        )

        lts_payload = models_lts.Payload(
            metadata = lts_metadata,
            results = lts_results,
        )

        yield lts_payload.dict(), lts_metadata.start, lts_metadata.end


def register_lts_metric(cluster_role, metric):
    pass

def _gather_prom_metrics(metrics, model) -> dict:
    data = {metric_name: metrics[metric_name]
            for metric_name in model.schema()["properties"].keys()}

    return model(**data)
