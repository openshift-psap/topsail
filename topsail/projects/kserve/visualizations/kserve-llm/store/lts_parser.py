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

    lts_payload.results = lts_results

    lts.validate_lts_payload(lts_payload, import_settings, reraise=must_validate)

    return lts_payload


def _generate_throughput(results):
    generated_tokens = 0

    llm_data = results.llm_load_test_output
    for idx, block in enumerate(llm_data):
        for detail in block["details"]:
            if detail.get("error"):
                continue # in this plot, ignore the latency if an error occured

            generated_tokens += int(detail["response"]["generatedTokens"])

    duration_s = (results.test_start_end.end - results.test_start_end.start).total_seconds()

    return generated_tokens / duration_s


def _generate_time_per_output_token(results):
    time_per_output_token = []

    llm_data = results.llm_load_test_output
    for idx, block in enumerate(llm_data):
        for detail in block["details"]:
            if detail.get("error"):
                continue # in this plot, ignore the latency if an error occured

            generated_tokens = int(detail["response"]["generatedTokens"])
            latency_ms = detail["latency"] / 1000 / 1000
            time_per_output_token.append(latency_ms / generated_tokens)

    return time_per_output_token


def _generate_time_to_first_token(results):
    return [] # cannot be computed yet


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
