import types
import yaml
import datetime

from .. import models
from ..models import lts as models_lts


def generate_lts_payload(results, import_settings):
    lts_payload = types.SimpleNamespace()

    lts_payload.metadata = generate_lts_metadata(results, import_settings)
    lts_payload.results = generate_lts_results(results)
    # lts_payload.kpis is generated in the helper store

    return lts_payload


def generate_lts_metadata(results, import_settings):
    metadata = types.SimpleNamespace()

    metadata.lts_schema_version = models_lts.LTS_SCHEMA_VERSION

    metadata.settings = generate_lts_settings(metadata, results, dict(import_settings))
    metadata.settings.ocp_version = "1.2.3"
    metadata.settings.ci_engine = "1.2.3"
    metadata.settings.run_id = "1.2.3"
    metadata.settings.test_path = "1.2.3"


    metadata.test_uuid = "77fd6668-6f72-442d-8390-10d4ea1c2d5e"
    metadata.start = datetime.datetime.now()
    metadata.end = datetime.datetime.now()

    return metadata


def generate_lts_results(results):
    results_lts = types.SimpleNamespace()

    results_lts.skeleton_results = True

    return results_lts


def _gather_prom_metrics(metrics, model) -> dict:
    data = {metric_name: metrics[metric_name]
            for metric_name in model.schema()["properties"].keys()}

    return model(**data)

def get_kpi_labels(lts_payload):
    kpi_labels = dict(lts_payload.metadata.settings.__dict__)

    kpi_labels["@timestamp"] = lts_payload.metadata.start.strftime('%Y-%m-%dT%H:%M:%S.%fZ') \
        if lts_payload.metadata.start else None
    kpi_labels["test_uuid"] = lts_payload.metadata.test_uuid

    return kpi_labels


def generate_lts_settings(lts_metadata, results, import_settings):
    lts_settings = types.SimpleNamespace()
    lts_settings.kpi_settings_version = models_lts.KPI_SETTINGS_VERSION


    return lts_settings
