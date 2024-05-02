import types
import json
import functools

import pytz

from .. import models
from . import lts_parser_helpers
from matrix_benchmarking.parse import json_dumper


def generate_lts_payload(results, import_settings):
    lts_payload = types.SimpleNamespace()

    lts_payload.metadata = generate_lts_metadata(results, import_settings)
    lts_payload.results = generate_lts_results(results)
    # lts_payload.kpis is generated in the helper store

    return lts_payload


def generate_lts_metadata(results, import_settings):
    metadata = types.SimpleNamespace()

    start_time: datetime.datetime = results.start_time
    end_time: datetime.datetime = results.end_time

    if start_time and start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=pytz.UTC)
    if end_time and end_time.tzinfo is None:
        end_time = end_time.replace(tzinfo=pytz.UTC)

    metadata.presets = results.test_config.get("ci_presets.names") or ["no_preset_defined"]
    metadata.test = results.test_config.get('tests.notebooks.identifier', "missing")

    if start_time:
        metadata.start = start_time.isoformat()
    if end_time:
        metadata.end = end_time.isoformat()

    metadata.rhods_version = results.rhods_info.full_version
    metadata.ocp_version = results.ocp_version
    metadata.settings = {'version': results.rhods_info.full_version, **lts_parser_helpers._parse_entry(import_settings)}
    metadata.test_uuid = results.test_uuid

    return metadata


def generate_lts_results(results):
    results_lts = types.SimpleNamespace()

    results_lts.users = lts_parser_helpers._decode_users(results)
    results_lts.config = results.test_config.yaml_file

    return results_lts
