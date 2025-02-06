import types
import yaml
import logging

from .. import models
from ..models.ilab import lts as models_lts


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

    if not results.ilab_metrics.summary or not results.ilab_metrics.summary.__dict__:
        logging.error("No ilab metrics available, not generating the LTS results.")
        return results_lts


        logging.error("No 'average_throughput' metrics available, not generating the LTS results.")
        return results_lts


    results_lts.average_throughput = results.ilab_metrics.summary.average_throughput \
        if hasattr(results.ilab_metrics.summary, "average_throughput") \
           else None

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
    lts_settings.accelerator_type = gpu_names or "no accelerator"

    replicas = results.job_config.get("pod_count", 1)
    accelerators_per_replica = results.job_config["gpu"]

    lts_settings.replicas = replicas
    lts_settings.accelerators_per_replica = accelerators_per_replica
    lts_settings.accelerator_count = replicas * accelerators_per_replica

    ####

    lts_settings.max_batch_len = results.workload_config.get("max_batch_len")
    lts_settings.num_epochs = results.workload_config.get("num_epochs")
    lts_settings.cpu_offload = results.workload_config.get("cpu_offload_optimizer")

    lts_settings.dataset_name = results.job_config["dataset_name"]

    ###

    lts_settings.ci_engine = results.from_env.test.ci_engine
    lts_settings.run_id = results.from_env.test.run_id
    lts_settings.test_path = results.from_env.test.test_path

    lts_settings.urls = results.from_env.test.urls

    return lts_settings
