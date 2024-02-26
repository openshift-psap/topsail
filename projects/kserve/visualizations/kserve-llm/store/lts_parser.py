import types
import logging

from .. import models
from ..models import lts as models_lts
from . import lts

def generate_lts_payload(results, lts_results, import_settings, must_validate=False):
    # To know the available metrics:
    # _=[print(m) for m in results.metrics["sutest"].keys()]

    lts_payload = types.SimpleNamespace()
    lts_payload.metadata = types.SimpleNamespace()

    lts_payload.metadata.start = results.test_start_end.start
    lts_payload.metadata.end = results.test_start_end.end

    lts_payload.metadata.presets = results.test_config.get("ci_presets.names") or ["no_preset_defined"]
    lts_payload.metadata.config = results.test_config.yaml_file

    lts_payload.metadata.ocp_version = results.ocp_version
    lts_payload.metadata.rhods_version = f"{results.rhods_info.version}-{results.rhods_info.createdAt.strftime('%Y-%m-%d')}"

    lts_payload.metadata.settings = dict(import_settings)
    lts_payload.metadata.test_uuid = results.test_uuid

    lts_payload.results = lts_results

    lts.validate_lts_payload(lts_payload, import_settings, reraise=must_validate)

    return lts_payload


def _generate_throughput(results):
    return results.llm_load_test_output["summary"]["throughput"]


def _generate_time_per_output_token(results):
    return results.llm_load_test_output["summary"]["tpot"]


def _generate_time_to_first_token(results):
    return results.llm_load_test_output["summary"]["ttft"]


def generate_lts_results(results):
    results_lts = types.SimpleNamespace()

    # Throughout value (scalar, in token/ms)
    results_lts.throughput = _generate_throughput(results)

    # Time Per Output Token value
    results_lts.time_per_output_token = _generate_time_per_output_token(results)

    # Time To First Token values for all of the calls (vector)
    results_lts.time_to_first_token = _generate_time_to_first_token(results)

    # Model Load Duration (scalar, in seconds)
    if results.predictor_pod and results.predictor_pod.load_time:
        results_lts.model_load_duration = results.predictor_pod.load_time.total_seconds()
    else:
        logging.error("Cannot set lts.results.model_load_duration: Predictor pod load time missing.")

    return results_lts


def _gather_prom_metrics(metrics, model) -> dict:
    data = {metric_name: metrics[metric_name]
            for metric_name in model.schema()["properties"].keys()}

    return model(**data)
