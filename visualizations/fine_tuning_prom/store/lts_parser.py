import types
import datetime
import yaml
import logging

from .. import models
from ..models import lts as models_lts

from . import FLAVOR, RAY_FLAVOR, FMS_FLAVOR, ILAB_FLAVOR

def generate_lts_payload(results, import_settings):
    lts_payload = types.SimpleNamespace()

    lts_payload.metadata = generate_lts_metadata(results, import_settings)
    lts_payload.results = generate_lts_results(results)
    # lts_payload.kpis is generated in the helper store

    return lts_payload


def generate_lts_settings(lts_metadata, results, import_settings):
    gpus = set([node_info.gpu.product for node_info in results.nodes_info.values() if node_info.gpu])
    gpu_names = "|".join(map(str, gpus))

    lts_settings = types.SimpleNamespace()
    lts_settings.kpi_settings_version = models_lts.KPI_SETTINGS_VERSION

    lts_settings.instance_type = results.test_config.get("clusters.sutest.compute.machineset.type")
    lts_settings.accelerator_name = gpu_names or "no accelerator"

    lts_settings.ocp_version = results.ocp_version
    version_name = results.test_config.get("rhods.catalog.version_name")
    lts_settings.rhoai_version = results.rhods_info.full_version

    lts_settings.ci_engine = results.from_env.test.ci_engine
    lts_settings.run_id = results.from_env.test.run_id
    lts_settings.test_path = results.from_env.test.test_path
    lts_settings.urls = results.from_env.test.urls

    lts_settings.test_mode = import_settings.get("mode")

    if FLAVOR == FMS_FLAVOR:
        replicas = results.job_config.get("pod_count", 1)
        accelerators_per_replica = results.job_config["gpu"]

        lts_settings.replicas = replicas
        lts_settings.accelerators_per_replica = accelerators_per_replica
        lts_settings.accelerator_count = replicas * accelerators_per_replica

        lts_settings.batch_size = results.tuning_config["per_device_train_batch_size"] * lts_settings.accelerator_count
        lts_settings.per_device_train_batch_size = results.tuning_config["per_device_train_batch_size"]
        lts_settings.max_seq_length = results.tuning_config["max_seq_length"]
        lts_settings.container_image = results.job_config["container_image"].split("/")[-1]

        lts_settings.model_name = results.job_config["model_name"]
        lts_settings.tuning_method = results.tuning_config.get("peft_method", "none")
        if lts_settings.tuning_method in ("none" , None):
            lts_settings.tuning_method = "full"

        lts_settings.lora_rank = results.tuning_config.get("r")
        lts_settings.lora_alpha = results.tuning_config.get("lora_alpha")
        lts_settings.lora_dropout = results.tuning_config.get("lora_dropout")
        lts_settings.lora_modules = ", ".join(sorted(results.tuning_config.get("target_modules", []))) or None

        lts_settings.dataset_name = results.job_config["dataset_name"]
        lts_settings.dataset_replication = results.job_config["dataset_replication"]

    return lts_settings


def generate_lts_metadata(results, import_settings):
    metadata = types.SimpleNamespace()

    try:
        start_ts = next(results.metrics["sutest"]["up"][0].values.keys().__iter__())
        end_ts = list(results.metrics["sutest"]["up"][0].values.keys())[-1]
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
