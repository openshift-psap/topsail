import types

from .. import models
from ..models import lts as models_lts
from . import lts

def generate_lts_payload(results, lts_results, import_settings, must_validate=False):
    # To know the available metrics:
    # _=[print(m) for m in results.metrics["sutest"].keys()]

    lts_payload = types.SimpleNamespace()
    lts_payload.metadata = types.SimpleNamespace()
    lts_payload.metadata.start = results.test_start_end_time.start
    lts_payload.metadata.end = results.test_start_end_time.end

    lts_payload.metadata.presets = results.test_config.get("ci_presets.names") or ["no_preset_defined"]
    lts_payload.metadata.config = results.test_config.yaml_file
    lts_payload.metadata.ocp_version = results.sutest_ocp_version
    lts_payload.metadata.settings = dict(import_settings)
    lts_payload.metadata.test_uuid = results.test_uuid

    lts_payload.results = lts_results

    lts.validate_lts_payload(lts_payload, import_settings, reraise=must_validate)

    return lts_payload


def generate_lts_results(results):
    results_lts = types.SimpleNamespace()

    results_lts.skeleton_results = True
    results_lts.metrics = _gather_prom_metrics(results.metrics["sutest"], models_lts.Metrics)

    return results_lts


def _gather_prom_metrics(metrics, model) -> dict:
    data = {metric_name: metrics[metric_name]
            for metric_name in model.schema()["properties"].keys()}

    return model(**data)
