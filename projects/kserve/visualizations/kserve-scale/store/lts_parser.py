import types
import datetime

from .. import models
from ..models import lts as models_lts
from . import lts


def generate_lts_payload(results, lts_results, import_settings, must_validate=False):
    lts_payload = types.SimpleNamespace()
    lts_payload.metadata = generate_lts_metadata(results, import_settings)
    lts_payload.results = lts_results

    lts.validate_lts_payload(lts_payload, import_settings, reraise=must_validate)

    return lts_payload


def generate_lts_metadata(results, import_settings):
    metadata = types.SimpleNamespace()

    metadata.start = results.test_start_end_time.start
    metadata.end = results.test_start_end_time.end

    metadata.presets = results.test_config.get("ci_presets.names") or ["no_preset_defined"]
    metadata.config = results.test_config.yaml_file
    metadata.settings = dict(import_settings)

    metadata.ocp_version = results.sutest_ocp_version
    metadata.rhoai_version = f"{results.rhods_info.version}-{results.rhods_info.createdAt.strftime('%Y-%m-%d')}"

    metadata.number_of_users = results.user_count
    metadata.number_of_inferenceservice_per_user = results.test_config.get("tests.scale.model.replicas")
    metadata.number_of_inferenceservices_to_create = results.user_count * metadata.number_of_inferenceservice_per_user

    return metadata


def generate_load_times(results):
    data = []

    for user_data in results.user_data.values():
        for res_name, res_times in user_data.resource_times.items():
            if res_times.kind != "InferenceService":
                continue

            data.append((res_times.conditions["Ready"] - res_times.creation).total_seconds())

    return data


def generate_test_duration(results):
    return (results.test_start_end_time.end - results.test_start_end_time.start).total_seconds()


def generate_lts_results(results):
    results_lts = types.SimpleNamespace()


    results_lts.inferenceservice_load_times = generate_load_times(results)
    results_lts.test_duration = generate_test_duration(results)
    results_lts.number_of_inferenceservices_loaded = len(results_lts.inferenceservice_load_times)
    results_lts.number_of_successful_users = results.success_count

    results_lts.metrics = _gather_prom_metrics(results.metrics["sutest"], models_lts.Metrics)

    return results_lts


def _gather_prom_metrics(metrics, model) -> dict:
    data = {metric_name: metrics[metric_name]
            for metric_name in model.schema()["properties"].keys()}

    return model(**data)
