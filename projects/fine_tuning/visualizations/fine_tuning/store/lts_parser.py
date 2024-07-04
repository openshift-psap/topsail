import types
import yaml

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
    metadata.start = results.test_start_end_time.start
    metadata.end = results.test_start_end_time.end

    metadata.presets = results.test_config.get("ci_presets.names") or ["no_preset_defined"]
    metadata.config = yaml.dump(results.test_config.yaml_file, indent=4, default_flow_style=False, sort_keys=False, width=1000)
    metadata.ocp_version = results.ocp_version
    metadata.settings = dict(import_settings)
    metadata.test_uuid = results.test_uuid

    metadata.settings = generate_lts_settings(metadata, results, dict(import_settings))

    return metadata


def generate_lts_results(results):
    results_lts = types.SimpleNamespace()

    if not results.sfttrainer_metrics.summary:
        return results_lts

    results_lts.dataset_tokens_per_second = results.sfttrainer_metrics.summary.train_tokens_per_second
    num_gpus = results.job_config["gpu"]
    results_lts.gpu_hours_per_million_tokens = 1/results.sfttrainer_metrics.summary.train_tokens_per_second * 1000000 / 60 / 60 * num_gpus
    results_lts.train_samples_per_second = results.sfttrainer_metrics.summary.train_samples_per_second

    return results_lts


def get_kpi_labels(lts_payload):
    kpi_labels = dict(lts_payload.metadata.settings.__dict__)

    kpi_labels["@timestamp"] = lts_payload.metadata.start.strftime('%Y-%m-%dT%H:%M:%S.%fZ') \
        if lts_payload.metadata.start else None
    kpi_labels["test_uuid"] = lts_payload.metadata.test_uuid

    return kpi_labels


def generate_lts_settings(lts_metadata, results, import_settings):
    gpus = set([node_info.gpu.product for node_info in results.nodes_info.values() if node_info.gpu and node_info.gpu.product])
    gpu_names = "|".join(map(str, gpus))

    lts_settings = types.SimpleNamespace()
    lts_settings.kpi_settings_version = models_lts.KPI_SETTINGS_VERSION

    lts_settings.ocp_version = results.ocp_version
    lts_settings.rhoai_version = results.rhods_info.full_version
    lts_settings.container_image = results.job_config["container_image"]
    lts_settings.instance_type = results.test_config.get("clusters.sutest.compute.machineset.type")

    lts_settings.model_name = results.job_config["model_name"]
    lts_settings.tuning_method = results.tuning_config.get("peft_method", "none")
    if lts_settings.tuning_method in ("none" , None):
        lts_settings.tuning_method = "full"

    lts_settings.accelerator_type = gpu_names or "no accelerator"
    lts_settings.accelerator_count = results.job_config["gpu"]
    lts_settings.batch_size = results.tuning_config["per_device_train_batch_size"] * lts_settings.accelerator_count

    lts_settings.ci_engine = results.from_env.test.ci_engine
    lts_settings.run_id = results.from_env.test.run_id
    lts_settings.test_path = results.from_env.test.test_path

    lts_settings.urls = results.from_env.test.urls

    return lts_settings
