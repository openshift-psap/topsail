import types
import pathlib
import logging
import datetime
import os
import uuid

import matrix_benchmarking.models as matbench_models
import matrix_benchmarking.parsing as matbench_parsing

from ..models.lts import LTS_SCHEMA_VERSION, KPI_SETTINGS_VERSION, Settings, Metadata, Results, Payload
from .parsers import parse_multiturn_benchmark_log, parse_guidellm_benchmark_log

def generate_lts_payload(results, import_settings):
    lts_payload = types.SimpleNamespace()

    lts_payload.metadata = generate_lts_metadata(results, import_settings)
    lts_payload.results = generate_lts_results(results)
    # lts_payload.kpis is generated in the helper store

    return lts_payload

def get_kpi_labels(lts_payload):
    kpi_labels = dict(lts_payload.metadata.settings.__dict__)
    return kpi_labels

def generate_lts_metadata(results, import_settings):
    lts_metadata = types.SimpleNamespace()

    # Generate settings
    settings_data = {
        "kpi_settings_version": KPI_SETTINGS_VERSION,
        "test_name": "llm-d-inference",
        "namespace": "llm-d-project",  # Default, could be read from config
        "multiturn_enabled": results.multiturn_benchmark is not None,
        "guidellm_enabled": len(results.guidellm_benchmarks) > 0,
    }

    # Add any additional settings from import_settings
    if import_settings:
        for key, value in import_settings.items():
            if key not in settings_data:
                settings_data[key] = value

    lts_metadata.settings = Settings(**settings_data)

    # Generate metadata
    lts_metadata.lts_schema_version = LTS_SCHEMA_VERSION
    lts_metadata.presets = []

    # Generate timestamps - use current time if not available
    start_time = datetime.datetime.now()
    end_time = start_time

    if hasattr(results, 'test_timestamp') and results.test_timestamp:
        start_time = results.test_timestamp
        end_time = results.test_timestamp

    lts_metadata.start = start_time
    lts_metadata.end = end_time
    lts_metadata.test_uuid = uuid.uuid4()
    lts_metadata.urls = None
    lts_metadata.exit_code = 0 if results.test_success else 1

    return lts_metadata

def generate_lts_results(results):
    results_lts = types.SimpleNamespace()

    results_lts.test_name = getattr(results, 'test_name', 'llm-d-inference')
    results_lts.test_success = getattr(results, 'test_success', True)
    results_lts.test_failure_reason = getattr(results, 'test_failure_reason', None)

    # Copy benchmark results
    results_lts.multiturn_benchmark = results.multiturn_benchmark
    results_lts.guidellm_benchmarks = results.guidellm_benchmarks

    # Copy data paths only if they have values
    multiturn_log_path = getattr(results, 'multiturn_log_path', None)
    if multiturn_log_path:
        results_lts.multiturn_log_path = multiturn_log_path

    guidellm_log_path = getattr(results, 'guidellm_log_path', None)
    if guidellm_log_path:
        results_lts.guidellm_log_path = guidellm_log_path

    prometheus_path = getattr(results, 'prometheus_path', None)
    if prometheus_path:
        results_lts.prometheus_path = prometheus_path

    return results_lts
