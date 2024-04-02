import types
import datetime
import yaml
import logging

from .. import models
from ..models import lts as models_lts


def generate_lts_payload(results, import_settings):
    lts_payload = types.SimpleNamespace()

    lts_payload.metadata = generate_lts_metadata(results, import_settings)
    lts_payload.results = generate_lts_results(results)
    # lts_payload.kpis is generated in the helper store

    return lts_payload


def generate_lts_settings(lts_metadata, results, import_settings):
    gpus = set([node_info.gpu.product for node_info in results.nodes_info.values() if node_info.gpu])
    gpu_names = "|".join(gpus)

    lts_settings = types.SimpleNamespace()
    lts_settings.kpi_settings_version = models_lts.KPI_SETTINGS_VERSION

    lts_settings.instance_type = results.test_config.get("clusters.sutest.compute.machineset.type")
    lts_settings.accelerator_name = gpu_names or "no accelerator"

    lts_settings.ocp_version = results.ocp_version
    version_name = results.test_config.get("rhods.catalog.version_name")
    lts_settings.rhoai_version = f"{results.rhods_info.version}-{version_name}+{results.rhods_info.createdAt.strftime('%Y-%m-%d')}"

    lts_settings.deployment_mode = "RawDeployment" if results.test_config.get("kserve.raw_deployment.enabled") else "Serverless"

    lts_settings.ci_engine = results.from_env.test.ci_engine
    lts_settings.run_id = results.from_env.test.run_id
    lts_settings.test_path = results.from_env.test.test_path
    lts_settings.urls = results.from_env.test.urls

    return lts_settings


def generate_lts_metadata(results, import_settings):
    metadata = types.SimpleNamespace()

    try:
        start_ts = next(results.metrics["sutest"]["kserve-e2e.* CPU usage"][0].values.keys().__iter__())
        end_ts = list(results.metrics["sutest"]["kserve-e2e.* CPU usage"][0].values.keys())[-1]
    except Exception as e:
        logging.error(f"Could not find the test start/end timestamps ... ({e})")
        start_ts = None
        end_ts = None

    metadata.lts_schema_version = models_lts.LTS_SCHEMA_VERSION

    metadata.start = datetime.datetime.utcfromtimestamp(start_ts) if start_ts else None
    metadata.end = datetime.datetime.utcfromtimestamp(end_ts) if end_ts else None

    metadata.presets = results.test_config.get("ci_presets.names") or ["no_preset_defined"]
    metadata.config = yaml.dump(results.test_config.yaml_file, indent=4, default_flow_style=False, sort_keys=False, width=1000)

    metadata.gpus = results.cluster_info.gpus

    metadata.test_uuid = results.test_uuid
    metadata.settings = generate_lts_settings(metadata, results, dict(import_settings))

    return metadata


def generate_lts_results(results):
    results_lts = types.SimpleNamespace()

    results_lts.metrics = _gather_prom_metrics(results.metrics["sutest"], models_lts.Metrics)

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
