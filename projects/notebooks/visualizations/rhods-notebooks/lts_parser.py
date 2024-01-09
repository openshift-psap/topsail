import types
import json
import functools

import pytz

from . import models
from . import horreum_lts_store
from matrix_benchmarking.parse import json_dumper


def generate_lts_payload(results, import_settings, must_validate=False):
    start_time: datetime.datetime = results.start_time
    end_time: datetime.datetime = results.end_time

    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=pytz.UTC)
    if end_time.tzinfo is None:
        end_time = end_time.replace(tzinfo=pytz.UTC)

    dict_payload = {
        "$schema": "urn:rhods-notebooks:1.0.0",
        "data": {
            "users": horreum_lts_store._decode_users(results),
            'metrics': horreum_lts_store._gather_prom_metrics(results),
            'thresholds': results.thresholds,
            'config': results.test_config.yaml_file,
            "cluster_info": horreum_lts_store._parse_entry(results.rhods_cluster_info),
        },
        "metadata": {
            "presets": results.test_config.get("ci_presets.names") or ["no_preset_defined"],
            "test": results.test_config.get('tests.notebooks.identifier', "missing"),
            "start": start_time.isoformat(),
            "end": end_time.isoformat(),
            'rhods_version': results.rhods_info.version,
            'ocp_version': results.sutest_ocp_version,
            "settings": {'version': results.rhods_info.version, **horreum_lts_store._parse_entry(import_settings)},
        }
    }

    return models.NotebookScalePayload.parse_obj(dict_payload)


def generate_lts_results(results):
    results_lts = types.SimpleNamespace()

    results_lts.benchmark_measures = results.notebook_benchmark

    return results_lts
