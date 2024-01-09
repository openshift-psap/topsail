import types
import json
import functools

import pytz

from .. import models
from ..models import lts as models_lts
from . import lts
from matrix_benchmarking.parse import json_dumper

def generate_lts_payload(results, lts_results, import_settings, must_validate=False):
    start_time = results.start_time
    end_time = results.end_time

    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=pytz.UTC)
    if end_time.tzinfo is None:
        end_time = end_time.replace(tzinfo=pytz.UTC)

    lts_payload = {
        "$schema": "urn:rhods-notebooks-perf:1.0.0",
        "metadata": {
            "start": start_time,
            "end": end_time,
            "presets": results.test_config.get("ci_presets.names") or ["no_preset_defined"],
            "config": results.test_config.yaml_file,
            "rhods_version": results.rhods_info.version,
            "ocp_version": results.sutest_ocp_version,
            "settings": import_settings,
            "test": results.test_config.get('tests.notebooks.identifier') or 'unknown'
        },
        "results": lts_results,
    }

    json_lts = json.dumps(lts_payload, indent=4, default=functools.partial(json_dumper, strict=False))
    parsed_lts = json.loads(json_lts)

    return models.lts.Payload.parse_obj(parsed_lts)


def generate_lts_results(results):
    results_lts = types.SimpleNamespace()

    results_lts.benchmark_measures = results.notebook_benchmark

    return results_lts
