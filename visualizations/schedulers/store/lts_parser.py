import types
import logging
import uuid

import pandas as pd
import statistics as stats

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

    results_lts.job_median_runtime = _get_median_runtime(results, results.test_case_properties.resource_kind)

    results_lts.pod_median_runtime = _get_pod_median_runtime(results)
    results_lts.max_concurrency = _get_max_concurrency(results)
    results_lts.job_theoretical_throughput = 1/(results_lts.job_median_runtime/60) * results_lts.max_concurrency
    results_lts.pod_theoretical_throughput = 1/(results_lts.pod_median_runtime/60) * results_lts.max_concurrency
    results_lts.test_duration = results_lts.time_to_test_sec
    results_lts.actual_throughput = results.test_case_properties.count / results_lts.test_duration * 60

    results_lts.avg_time_per_job = results_lts.test_duration / (results.test_case_properties.count / results_lts.max_concurrency)
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

    target_kind = results.test_case_properties.resource_kind.title()
    if target_kind == "Pytorchjob":
        target_kind = "PyTorchJob"

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


def _get_median_runtime(results, kind):
    durations = []
    for resource_name, resource_times in results.resource_times.items():
        if resource_times.kind.lower() != kind.lower(): continue
        if resource_times.duration is None:
            continue
        durations.append(resource_times.duration)

    if len(durations) <= 2:
        return None

    return stats.median(durations)


def _get_pod_median_runtime(results):
    durations = []

    for pod_times in results.pod_times:
        try:
            duration = pod_times.container_finished - pod_times.start_time
        except AttributeError:
            continue

        durations.append(duration.total_seconds())

    if len(durations) <= 2:
        return None

    return stats.median(durations)


def _get_max_concurrency(results):
    from ..plotting import mapping

    data = mapping.ResourceMappingTimeline_generate_data_by_all(results)
    df = pd.DataFrame(data)

    return df["Count"].max()
