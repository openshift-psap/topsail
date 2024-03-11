import types
import datetime
import yaml

from .. import models
from ..models import lts as models_lts
from . import lts

def generate_lts_payload(results, lts_results, import_settings, must_validate=False):
    # To know the available metrics:
    # _=[print(m) for m in results.metrics["sutest"].keys()]

    lts_payload = types.SimpleNamespace()
    lts_payload.metadata = generate_lts_metadata(results, import_settings)
    lts_payload.results = lts_results

    lts.validate_lts_payload(lts_payload, import_settings, reraise=must_validate)

    return lts_payload


def generate_lts_metadata(results, import_settings):
    metadata = types.SimpleNamespace()

    start_ts = next(results.metrics["sutest"]["watsonx-e2e.* CPU usage"][0].values.keys().__iter__())
    end_ts = list(results.metrics["sutest"]["watsonx-e2e.* CPU usage"][0].values.keys())[-1]

    metadata.start = datetime.datetime.utcfromtimestamp(start_ts)
    metadata.end = datetime.datetime.utcfromtimestamp(end_ts)

    metadata.presets = results.test_config.get("ci_presets.names") or ["no_preset_defined"]
    metadata.config = config = yaml.dump(results.test_config.yaml_file, indent=4, default_flow_style=False, sort_keys=False, width=1000)
    metadata.settings = dict(import_settings)

    metadata.gpus = results.cluster_info.gpus

    metadata.test_uuid = results.test_uuid

    return metadata


def generate_lts_results(results):
    results_lts = types.SimpleNamespace()

    results_lts.metrics = _gather_prom_metrics(results.metrics["sutest"], models_lts.Metrics)

    return results_lts


def _gather_prom_metrics(metrics, model) -> dict:
    data = {metric_name: metrics[metric_name]
            for metric_name in model.schema()["properties"].keys()}

    return model(**data)
