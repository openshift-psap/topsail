import types

from .. import models
from ..models import lts as models_lts
from . import lts


def generate_lts_payload(results, lts_results, import_settings, must_validate=False):
    # To know the available metrics:
    # _=[print(m) for m in results.metrics["sutest"].keys()]g

    lts_payload = types.SimpleNamespace()
    lts_payload.metadata = generate_lts_metadata(results, import_settings)
    lts_payload.results = lts_results

    lts.validate_lts_payload(lts_payload, import_settings, reraise=must_validate)

    return lts_payload


def generate_lts_metadata(results, import_settings):
    metadata = types.SimpleNamespace()

    metadata.start = results.test_start_end_time.start
    metadata.end = results.test_start_end_time.end

    metadata.presets = results.test_config.get("ci_presets.names") or ["no_preset_defined"]
    metadata.config = results.test_config.yaml_file
    metadata.ocp_version = results.sutest_ocp_version
    metadata.settings = dict(import_settings)
    metadata.test_uuid = results.test_uuid

    return metadata


def generate_lts_results(results):
    results_lts = types.SimpleNamespace()

    results_lts.skeleton_results = True
    results_lts.metrics = _gather_prom_metrics(results.metrics["sutest"], models_lts.Metrics)

    return results_lts


def _gather_prom_metrics(metrics, model) -> dict:
    data = {metric_name: metrics[metric_name]
            for metric_name in model.schema()["properties"].keys()}

    return model(**data)
