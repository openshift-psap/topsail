import types
import logging
import uuid

from .. import models
from ..models import lts as models_lts

def generate_lts_metadata(results, import_settings):
    metadata = types.SimpleNamespace()
    metadata.lts_schema_version = models_lts.LTS_SCHEMA_VERSION
    metadata.start = results.test_start_end_time.start
    metadata.end = results.test_start_end_time.end
    metadata.presets = results.test_config.get("ci_presets.names") or ["no_preset_defined"]
    metadata.config = results.test_config.yaml_file

    metadata.test_uuid = results.test_uuid

    metadata.settings = generate_lts_settings(metadata, results, dict(import_settings))

    return metadata


def generate_lts_results(results):
    results_lts = types.SimpleNamespace()

    results_lts.time_to_last_schedule_sec, last_schedule_time = \
        _get_time_to_last_schedule(results)

    results_lts.time_to_last_launch_sec, last_launch_time = \
        _get_time_to_last_launch(results)

    results_lts.last_launch_to_last_schedule_sec = \
        (last_schedule_time - last_launch_time).total_seconds() \
        if last_schedule_time and last_launch_time else None

    results_lts.time_to_test_sec = (results.test_start_end_time.end - results.test_start_end_time.start).total_seconds()

    return results_lts


def generate_lts_payload(results, import_settings):
    # To know the available metrics:
    # _=[print(m) for m in results.metrics["sutest"].keys()]

    payload = types.SimpleNamespace()

    payload.metadata = generate_lts_metadata(results, import_settings)
    payload.results = generate_lts_results(results)
    # lts_payload.kpis is generated in the helper store

    return payload

# ---

def _get_time_to_last_launch(results):
    if not results.resource_times:
        return 0, None


    target_kind = {
        "job": "Job",
        "mcad": "AppWrapper",
        "kueue": "Job",
        "coscheduling": "Job",
    }[results.test_case_properties.mode]

    resource_time = sorted([resource_time for resource_time in results.resource_times.values() if resource_time.kind == target_kind], key=lambda t: t.creation)[-1]

    start_time = results.test_start_end_time.start

    last_launch = resource_time.creation
    return (last_launch - start_time).total_seconds(), last_launch


def _get_time_to_last_schedule(results):
    if not results.pod_times:
        return 0, None

    pod_time = sorted(results.pod_times, key=lambda t: t.pod_scheduled)[-1]

    start_time = results.test_start_end_time.start

    last_schedule = pod_time.pod_scheduled
    return (last_schedule - start_time).total_seconds(), last_schedule


def generate_lts_settings(lts_metadata, results, import_settings):
    lts_settings = types.SimpleNamespace()
    lts_settings.kpi_settings_version = models_lts.KPI_SETTINGS_VERSION

    lts_settings.ocp_version = results.ocp_version
    lts_settings.rhoai_version = results.rhods_info.full_version
    lts_settings.ci_engine = results.from_env.test.ci_engine
    lts_settings.run_id = results.from_env.test.run_id
    lts_settings.test_path = results.from_env.test.test_path
    lts_settings.urls = results.from_env.test.urls

    test_case_properties = results.test_case_properties
    lts_settings.test_mode = test_case_properties.mode
    lts_settings.obj_count = test_case_properties.count
    lts_settings.total_pod_count = test_case_properties.total_pod_count
    lts_settings.pod_runtime = test_case_properties.pod_runtime
    lts_settings.launch_duration = test_case_properties.launch_duration

    return lts_settings


def get_kpi_labels(lts_payload):
    kpi_labels = dict(lts_payload.metadata.settings.__dict__)

    kpi_labels["@timestamp"] = lts_payload.metadata.start.strftime('%Y-%m-%dT%H:%M:%S.%fZ') \
        if lts_payload.metadata.start else None

    kpi_labels["test_uuid"] = lts_payload.metadata.test_uuid

    return kpi_labels
