import types
import logging
import pytz
import pathlib
import yaml

from .. import models
from ..models import lts as models_lts

def generate_lts_payload(results, import_settings):
    lts_payload = types.SimpleNamespace()

    lts_payload.metadata = generate_lts_metadata(results, import_settings)
    lts_payload.results = generate_lts_results(results)
    # lts_payload.kpis is generated in the helper store

    return lts_payload


def generate_lts_settings(lts_metadata, results, import_settings):
    gpus = set([node_info.gpu.product for node_info in results.nodes_info.values() if node_info.gpu and node_info.gpu.product])
    gpu_names = "|".join(gpus)

    lts_settings = types.SimpleNamespace()
    lts_settings.kpi_settings_version = models_lts.KPI_SETTINGS_VERSION

    lts_settings.instance_type = results.test_config.get("clusters.sutest.compute.machineset.type")

    lts_settings.ocp_version = results.ocp_version
    version_name = results.test_config.get("rhods.catalog.version_name")
    lts_settings.rhoai_version = results.rhods_info.full_version

    lts_settings.ci_engine = results.from_env.test.ci_engine
    lts_settings.run_id = results.from_env.test.run_id
    lts_settings.test_path = results.from_env.test.test_path
    lts_settings.urls = results.from_env.test.urls

    return lts_settings


def generate_lts_metadata(results, import_settings):
    lts_metadata = types.SimpleNamespace()

    lts_metadata.lts_schema_version = models_lts.LTS_SCHEMA_VERSION
    lts_metadata.start = results.tester_job.creation_time
    lts_metadata.end = results.tester_job.completion_time
    lts_metadata.presets = results.test_config.get("ci_presets.names") or ["no_preset_defined"]
    lts_metadata.settings = dict(import_settings)
    lts_metadata.ocp_version = results.ocp_version
    lts_metadata.rhods_version = results.rhods_info.full_version
    lts_metadata.user_count = results.user_count
    lts_metadata.config = yaml.dump(results.test_config.yaml_file, indent=4, default_flow_style=False, sort_keys=False, width=1000)
    lts_metadata.test_uuid = results.test_uuid
    lts_metadata.settings = generate_lts_settings(lts_metadata, results, dict(import_settings))

    return lts_metadata


def generate_lts_results(results):
    lts_results = types.SimpleNamespace()

    # nothing at the moment

    return lts_results


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
