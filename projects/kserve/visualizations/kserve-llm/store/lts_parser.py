import types
import logging
import pytz
import pathlib

from .. import models
from ..models import lts as models_lts
from . import lts

def generate_lts_payload(results, import_settings, must_validate=False):
    # To know the available metrics:
    # _=[print(m) for m in results.metrics["sutest"].keys()]

    lts_payload = types.SimpleNamespace()
    lts_payload.results = generate_lts_results(results)
    lts_payload.metadata = generate_lts_metadata(results, import_settings)
    lts_payload.kpis = lts.generate_lts_kpis(lts_payload)
    lts.validate_lts_payload(lts_payload, import_settings, reraise=must_validate)

    return lts_payload


def _generate_throughput(results):
    if not results.llm_load_test_output: return None

    return results.llm_load_test_output["summary"]["throughput"]


def _generate_time_per_output_token(results):
    if not results.llm_load_test_output: return None

    tpot = dict(results.llm_load_test_output["summary"]["tpot"])
    tpot["values"] = [x["tpot"] for x in results.llm_load_test_output["results"] if x["tpot"]]
    return types.SimpleNamespace(**tpot)

def _generate_inter_token_latency(results):
    if not results.llm_load_test_output: return None

    itl = dict(results.llm_load_test_output["summary"]["itl"])
    itl["values"] = [x["itl"] for x in results.llm_load_test_output["results"] if x["itl"]]
    return types.SimpleNamespace(**itl)


def _generate_time_to_first_token(results):
    if not results.llm_load_test_output: return None

    ttft = dict(results.llm_load_test_output["summary"]["ttft"])
    ttft["values"] = [x["ttft"] for x in results.llm_load_test_output["results"] if x["ttft"]]
    return types.SimpleNamespace(**ttft)


def _generate_failures(results):
    if not results.llm_load_test_output: return None

    return results.llm_load_test_output["summary"]["total_failures"]


def _is_streaming(results):
    return results.test_config.get("tests.e2e.llm_load_test.args.streaming")


def generate_lts_settings(lts_metadata, results, import_settings):
    gpus = set([node_info.gpu.product for node_info in results.nodes_info.values() if node_info.gpu])
    gpu_names = "|".join(gpus)

    lts_settings = types.SimpleNamespace()

    lts_settings.instance_type = results.test_config.get("clusters.sutest.compute.machineset.type")
    lts_settings.accelerator_name = gpu_names

    lts_settings.ocp_version = lts_metadata.ocp_version
    lts_settings.rhoai_version = lts_metadata.rhods_version
    lts_settings.deployment_mode = "RawDeployment" if results.test_config.get("kserve.raw_deployment.enabled") else "Serverless"
    lts_settings.model_name = import_settings["model_name"]
    lts_settings.runtime_image = results.test_config.get("kserve.model.serving_runtime.kserve.image").split(":")[1]
    lts_settings.min_pod_replicas = results.inference_service.min_replicas
    lts_settings.max_pod_replicas = results.inference_service.max_replicas
    lts_settings.virtual_users = results.test_config.get("tests.e2e.llm_load_test.args.concurrency")
    lts_settings.test_duration = results.test_config.get("tests.e2e.llm_load_test.args.duration")
    lts_settings.dataset_name = pathlib.Path(results.llm_load_test_config.get("dataset.file")).name
    lts_settings.test_mode = import_settings.get("mode") or None
    lts_settings.ci_engine = results.from_env.test.ci_engine
    lts_settings.run_id = results.from_env.test.run_id
    lts_settings.test_path = results.from_env.test.test_path
    lts_settings.urls = results.from_env.test.urls
    lts_settings.streaming = _is_streaming(results)

    return lts_settings


def generate_lts_metadata(results, import_settings):
    start_time = None
    end_time = None

    if results.test_start_end:
        start_time = results.test_start_end.start
        end_time = results.test_start_end.end

        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=pytz.UTC)
        if end_time.tzinfo is None:
            end_time = end_time.replace(tzinfo=pytz.UTC)

    lts_metadata = types.SimpleNamespace()
    lts_metadata.start = start_time
    lts_metadata.end = end_time
    lts_metadata.presets = results.test_config.get("ci_presets.names") or ["no_preset_defined"]
    lts_metadata.config = results.test_config.yaml_file
    lts_metadata.ocp_version = results.ocp_version
    lts_metadata.rhods_version = f"{results.rhods_info.version}-{results.rhods_info.createdAt.strftime('%Y-%m-%d')}"
    lts_metadata.test_uuid = results.test_uuid
    lts_metadata.settings = generate_lts_settings(lts_metadata, results, dict(import_settings))
    lts_metadata.run_id = results.from_env.test.run_id
    lts_metadata.test_path = results.from_env.test.test_path
    lts_metadata.urls = results.from_env.test.urls
    lts_metadata.ci_engine = results.from_env.test.ci_engine

    return lts_metadata


def generate_lts_results(results):
    results_lts = types.SimpleNamespace()

    # Throughout value (scalar, in token/ms)
    results_lts.throughput = _generate_throughput(results)

    # Time Per Output Token value
    results_lts.time_per_output_token = _generate_time_per_output_token(results)

    results_lts.streaming = _is_streaming(results)

    if results_lts.streaming:
        # Inter Token Latency (ms)
        results_lts.inter_token_latency = _generate_inter_token_latency(results)

        # Time To First Token values for all of the calls (vector)
        results_lts.time_to_first_token = _generate_time_to_first_token(results)
    else:
        results_lts.inter_token_latency = None
        results_lts.time_to_first_token = None

    # Model Load Duration (scalar, in seconds)
    if results.predictor_pod and results.predictor_pod.load_time:
        results_lts.model_load_duration = results.predictor_pod.load_time.total_seconds()
    else:
        logging.error("Cannot set lts.results.model_load_duration: Predictor pod load time missing.")

    # Number of failures
    results_lts.failures = _generate_failures(results)

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
