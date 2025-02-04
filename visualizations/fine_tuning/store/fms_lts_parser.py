import types
import yaml
import logging

from .. import models
from ..models.fms import lts as models_lts


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

    if not results.sfttrainer_metrics.summary or not results.sfttrainer_metrics.summary.__dict__:
        return results_lts

    num_gpus = results.job_config["gpu"]
    if not num_gpus:
        num_gpus = 1 # prevent div by 0 crashes

    train_tokens_per_second = results.sfttrainer_metrics.summary.train_tokens_per_second * num_gpus
    results_lts.train_tokens_per_second = train_tokens_per_second
    results_lts.dataset_tokens_per_second = results.sfttrainer_metrics.summary.dataset_tokens_per_second

    results_lts.gpu_hours_per_million_tokens = 1/results.sfttrainer_metrics.summary.dataset_tokens_per_second * 1000000 / 60 / 60 * num_gpus
    results_lts.train_samples_per_second = results.sfttrainer_metrics.summary.train_samples_per_second

    results_lts.train_steps_per_second = results.sfttrainer_metrics.summary.train_steps_per_second
    results_lts.train_runtime = results.sfttrainer_metrics.summary.train_runtime
    results_lts.train_tokens_per_gpu_per_second = train_tokens_per_second / num_gpus

    results_lts.dataset_tokens_per_second_per_gpu = results.sfttrainer_metrics.summary.dataset_tokens_per_second / num_gpus
    results_lts.avg_tokens_per_sample = results.sfttrainer_metrics.dataset_stats.avg_tokens_per_sample
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

    lts_settings.container_image = results.job_config["container_image"].split("/")[-1]
    lts_settings.instance_type = results.test_config.get("clusters.sutest.compute.machineset.type")

    lts_settings.model_name = results.job_config["model_name"]
    lts_settings.tuning_method = results.workload_config.get("peft_method", "none")
    if lts_settings.tuning_method in ("none" , None):
        lts_settings.tuning_method = "full"

    lts_settings.accelerator_type = gpu_names or "no accelerator"

    replicas = results.job_config.get("pod_count", 1)
    accelerators_per_replica = results.job_config["gpu"]

    lts_settings.replicas = replicas
    lts_settings.accelerators_per_replica = accelerators_per_replica
    lts_settings.accelerator_count = replicas * accelerators_per_replica

    lts_settings.per_device_train_batch_size = results.workload_config["per_device_train_batch_size"]
    lts_settings.batch_size = results.workload_config["per_device_train_batch_size"] * lts_settings.accelerator_count
    lts_settings.max_seq_length = results.workload_config["max_seq_length"]

    lts_settings.lora_rank = results.workload_config.get("r")
    lts_settings.lora_alpha = results.workload_config.get("lora_alpha")
    lts_settings.lora_dropout = results.workload_config.get("lora_dropout")
    lts_settings.lora_modules = ", ".join(sorted(results.workload_config.get("target_modules", []))) or None

    lts_settings.dataset_name = results.job_config["dataset_name"]
    lts_settings.dataset_replication = results.job_config["dataset_replication"]

    lts_settings.ci_engine = results.from_env.test.ci_engine
    lts_settings.run_id = results.from_env.test.run_id
    lts_settings.test_path = results.from_env.test.test_path

    lts_settings.urls = results.from_env.test.urls

    return lts_settings
