import types
import logging
import pytz

from .. import models
from ..models import lts as models_lts
from . import lts

def generate_lts_payload(results, lts_results, import_settings, must_validate=False):
    # To know the available metrics:
    # _=[print(m) for m in results.metrics["sutest"].keys()]

    lts_payload = types.SimpleNamespace()
    lts_payload.metadata = generate_lts_metadata(results, import_settings)
    lts_payload.results = lts_results
    lts_payload.kpis = lts.generate_lts_kpis(lts_payload)
    lts.validate_lts_payload(lts_payload, import_settings, reraise=must_validate)

    return lts_payload

def _generate_throughput(results):
    return results.llm_load_test_output["summary"]["throughput"]


def _generate_time_per_output_token(results):
    tpot = dict(results.llm_load_test_output["summary"]["tpot"])
    tpot["values"] = [x["tpot"] for x in results.llm_load_test_output["results"]]
    return tpot

def _generate_time_to_first_token(results):
    ttft = dict(results.llm_load_test_output["summary"]["ttft"])
    ttft["values"] = [x["ttft"] for x in results.llm_load_test_output["results"]]
    return ttft

def generate_lts_settings(lts_metadata, import_settings):

    return models_lts.Settings(
        ocp_version = lts_metadata.ocp_version,
        rhoai_version = lts_metadata.rhods_version,
        tgis_image_version = lts_metadata.tgis_image_version,
        model_name = import_settings["model_name"],
        mode = import_settings["mode"],
    )

def generate_lts_metadata(results, import_settings):
    start_time = results.test_start_end.start
    end_time = results.test_start_end.end

    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=pytz.UTC)
    if end_time.tzinfo is None:
        end_time = end_time.replace(tzinfo=pytz.UTC)

    lts_metadata = types.SimpleNamespace()
    lts_metadata.start = results.test_start_end.start
    lts_metadata.end = results.test_start_end.end
    lts_metadata.presets = results.test_config.get("ci_presets.names") or ["no_preset_defined"]
    lts_metadata.config = results.test_config.yaml_file
    lts_metadata.ocp_version = results.ocp_version
    lts_metadata.rhods_version = f"{results.rhods_info.version}-{results.rhods_info.createdAt.strftime('%Y-%m-%d')}"
    lts_metadata.tgis_image_version = results.test_config.get("kserve.model.serving_runtime.kserve.image") or "None"
    lts_metadata.test_uuid = results.test_uuid
    lts_metadata.settings = generate_lts_settings(lts_metadata, dict(import_settings))

    return lts_metadata

def generate_lts_results(results):
    results_lts = {}
    # Throughout value (scalar, in token/ms)
    results_lts["throughput"] = _generate_throughput(results)

    # Time Per Output Token value
    results_lts["time_per_output_token"] = _generate_time_per_output_token(results)

    # Time To First Token values for all of the calls (vector)
    results_lts["time_to_first_token"] = _generate_time_to_first_token(results)

    # Model Load Duration (scalar, in seconds)
    if results.predictor_pod and results.predictor_pod.load_time:
        results_lts["model_load_duration"] = results.predictor_pod.load_time.total_seconds()
    else:
        logging.error("Cannot set lts.results.model_load_duration: Predictor pod load time missing.")

    return models.lts.Results.parse_obj(results_lts)


def _gather_prom_metrics(metrics, model) -> dict:
    data = {metric_name: metrics[metric_name]
            for metric_name in model.schema()["properties"].keys()}

    return model(**data)

def get_kpi_labels(lts_payload):
    kpi_labels = dict(lts_payload.metadata.settings)

    kpi_labels["@timestamp"] = lts_payload.metadata.start.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
    kpi_labels["test_uuid"] = lts_payload.metadata.test_uuid

    return kpi_labels
