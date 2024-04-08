import types
import logging
import pytz
import pathlib
import yaml

from .. import models
from ..models import lts as models_lts

def generate_lts_payload(results, import_settings):
    lts_payload = types.SimpleNamespace()

    lts_payload.metadata = generate_lts_metadata(results, import_settings)
    lts_payload.results = generate_lts_results(results)
    # lts_payload.kpis is generated in the helper store

    return lts_payload


def generate_lts_metadata(results, import_settings):
    lts_metadata = types.SimpleNamespace()

    lts_metadata.start = results.tester_job.creation_time
    lts_metadata.end = results.tester_job.completion_time
    lts_metadata.presets = results.test_config.get("ci_presets.names") or ["no_preset_defined"]
    lts_metadata.settings = dict(import_settings)
    lts_metadata.ocp_version = results.ocp_version
    lts_metadata.rhods_version = results.rhods_info.full_version
    lts_metadata.user_count = results.user_count
    lts_metadata.config = yaml.dump(results.test_config.yaml_file, indent=4, default_flow_style=False, sort_keys=False, width=1000)
    lts_metadata.test_uuid = results.test_uuid


    return lts_metadata


def generate_lts_results(results):
    lts_results = types.SimpleNamespace()

    # nothing at the moment

    return lts_results


def _gather_prom_metrics(metrics, model) -> dict:
    data = {metric_name: metrics[metric_name]
            for metric_name in model.schema()["properties"].keys()}

    return model(**data)
