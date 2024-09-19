import types
import logging
import pytz
import pathlib
import yaml
import numpy as np
from typing import List
from functools import reduce
import re

from .. import models
from ..models import lts as models_lts

def generate_lts_payload(results, import_settings):
    lts_payload = types.SimpleNamespace()

    lts_payload.metadata = generate_lts_metadata(results, import_settings)
    lts_payload.results = generate_lts_results(results)
    # lts_payload.kpis is generated in the helper store

    return lts_payload


def generate_lts_settings(lts_metadata, results, import_settings):
    lts_settings = types.SimpleNamespace()
    lts_settings.kpi_settings_version = models_lts.KPI_SETTINGS_VERSION

    lts_settings.instance_type = results.test_config.get("clusters.sutest.compute.machineset.type")
    lts_settings.user_count = results.user_count
    lts_settings.pipelines_per_user = results.pipelines_per_user
    lts_settings.runs_per_pipeline = results.runs_per_pipeline
    lts_settings.project_count = results.project_count
    lts_settings.run_delay = results.run_delay
    lts_settings.user_pipeline_delay = results.user_pipeline_delay
    lts_settings.sleep_factor = results.sleep_factor
    lts_settings.wait_for_run_completion = results.wait_for_run_completion
    lts_settings.notebook = results.notebook

    lts_settings.ocp_version = results.ocp_version
    lts_settings.rhoai_version = results.rhods_info.full_version

    lts_settings.ci_engine = results.from_env.test.ci_engine
    lts_settings.run_id = results.from_env.test.run_id
    lts_settings.test_path = results.from_env.test.test_path
    lts_settings.urls = results.from_env.test.urls

    return lts_settings


def generate_lts_metadata(results, import_settings):
    lts_metadata = types.SimpleNamespace()

    lts_metadata.lts_schema_version = models_lts.LTS_SCHEMA_VERSION
    lts_metadata.start = results.tester_job.creation_time
    lts_metadata.end = results.tester_job.completion_time
    lts_metadata.presets = results.test_config.get("ci_presets.names") or ["no_preset_defined"]
    lts_metadata.settings = dict(import_settings)
    lts_metadata.ocp_version = results.ocp_version
    lts_metadata.rhods_version = results.rhods_info.full_version
    lts_metadata.config = yaml.dump(results.test_config.yaml_file, indent=4, default_flow_style=False, sort_keys=False, width=1000)
    lts_metadata.test_uuid = results.test_uuid
    lts_metadata.settings = generate_lts_settings(lts_metadata, results, dict(import_settings))

    return lts_metadata


def generate_lts_results(results):
    lts_results = types.SimpleNamespace()

    lts_results.run_latency = _generate_run_latency(results)
    lts_results.run_duration = _generate_run_duration(results)

    return lts_results

def _generate_run_latency(results):
    run_latency = {}

    workflow_mapping = {}
    workflow_ordering = {}
    data = {}
    # Assemble the workflow names
    for user_idx, user_data in results.user_data.items():
        for resource_name, creation_time in user_data.resource_times.items():
            resource_type, resource_id = resource_name.split("/")
            if resource_type == "Workflow":
                workflow_mapping[resource_id] = user_idx
                if user_idx not in workflow_ordering:
                    workflow_ordering[user_idx] = []
                workflow_ordering[user_idx].append({"name": resource_name, "creation_time": creation_time})
                workflow_ordering[user_idx] = sorted(workflow_ordering[user_idx], key=lambda x: x["creation_time"])
    for user_idx, user_data in results.user_data.items():
        for resource_name, creation_time in user_data.resource_times.items():
            resource_key = re.sub(r'n([0-9]+)-', "nX-", resource_name)
            if resource_name.split("/")[0] == "Workflow":
                workflow_run_name = user_data.workflow_run_names[resource_name.split("/")[1]]
                resource_key = f"Workflow/{workflow_run_name}"
                resource_key = resource_key.replace(f"user{user_idx}-", "")
                if resource_key not in data:
                    data[resource_key] = []
                data[resource_key].append((user_data.workflow_start_times[resource_name.split("/")[1]] - user_data.submit_run_times[workflow_run_name]).total_seconds())

    run_latency = _generate_dsp_test_stats(list(reduce(lambda l, r: l + r, data.values(), [])))
    medians = np.array([np.median(d[1]) for d in sorted(data.items())])
    A = np.vstack([np.arange(len(medians)), np.ones(len(medians))]).T
    slope, _ = np.linalg.lstsq(A, medians, rcond=None)[0]
    run_latency["degrade_speed"] = slope
    return types.SimpleNamespace(**run_latency)

def _generate_run_duration(results):
    run_duration = {}

    workflow_mapping = {}
    workflow_ordering = {}
    data = {}
    # Assemble the workflow names
    for user_idx, user_data in results.user_data.items():
        for resource_name, creation_time in user_data.resource_times.items():
            resource_type, resource_id = resource_name.split("/")
            if resource_type == "Workflow":
                workflow_mapping[resource_id] = user_idx
                if user_idx not in workflow_ordering:
                    workflow_ordering[user_idx] = []
                workflow_ordering[user_idx].append({"name": resource_name, "creation_time": creation_time})
                workflow_ordering[user_idx] = sorted(workflow_ordering[user_idx], key=lambda x: x["creation_time"])
    for user_idx, user_data in results.user_data.items():
        for resource_name, creation_time in user_data.resource_times.items():
            resource_key = re.sub(r'n([0-9]+)-', "nX-", resource_name)
            if resource_name.split("/")[0] == "Workflow":
                workflow_run_name = user_data.workflow_run_names[resource_name.split("/")[1]]
                resource_key = f"Workflow/{workflow_run_name}"
                resource_key = resource_key.replace(f"user{user_idx}-", "")
                if workflow_run_name in user_data.complete_run_times:
                    if resource_key not in data:
                        data[resource_key] = []
                    data[resource_key].append((user_data.complete_run_times[workflow_run_name] - user_data.workflow_start_times[resource_name.split("/")[1]]).total_seconds())

    run_duration = _generate_dsp_test_stats(list(reduce(lambda l, r: l + r, data.values(), [])))
    medians = np.array([np.median(d[1]) for d in sorted(data.items())])
    A = np.vstack([np.arange(len(medians)), np.ones(len(medians))]).T
    slope, _ = np.linalg.lstsq(A, medians, rcond=None)[0]
    run_duration["degrade_speed"] = slope

    return types.SimpleNamespace(**run_duration)

def _generate_dsp_test_stats(data: List[float]):
    test_stats = {}

    test_stats["values"] = data
    test_stats["min"] = np.min(data)
    test_stats["max"] = np.max(data)
    test_stats["median"] = np.median(data)
    test_stats["mean"] = np.mean(data)
    test_stats["percentile_80"] = np.percentile(data, 80)
    test_stats["percentile_90"] = np.percentile(data, 90)
    test_stats["percentile_95"] = np.percentile(data, 95)
    test_stats["percentile_99"] = np.percentile(data, 99)

    return test_stats

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
