import types
import datetime
import logging
import pytz
import json
import functools

import matrix_benchmarking.common as common
from matrix_benchmarking.parse import json_dumper

from ..import models
from . import lts_parser
from ..models import lts as models_lts
from ..models import kpi as models_kpi

def build_lts_payloads():

    for entry in common.Matrix.processed_map.values():
        results = entry.results
        lts_payload = results.lts

        validate_lts_payload(lts_payload, entry.import_settings, reraise=True)

        yield lts_payload, lts_payload.metadata.start, lts_payload.metadata.end


def validate_lts_payload(payload, import_settings, reraise=False):
    try:
        json_lts = json.dumps(payload, indent=4, default=functools.partial(json_dumper, strict=False))
    except ValueError as e:
        logging.error(f"Couldn't dump the lts_payload into JSON :/ {e}")

        if reraise:
            raise

        return False

    parsed_lts = json.loads(json_lts)
    try:
        models.lts.Payload.parse_obj(parsed_lts)
        return True

    except Exception as e:
        logging.error(f"lts-error: Failed to validate the generated LTS payload against the model")
        logging.error(f"lts-error: entry settings: {import_settings}")

        if reraise:
            raise

        logging.error(f"lts-error: validation issue(s): {e}")

        return False


def generate_lts_kpis(lts_payload):

    kpis = {}
    min_value = min(lts_payload.results.benchmark_measures.measures)
    max_value = max(lts_payload.results.benchmark_measures.measures)
    diff_value = max_value - min_value

    for name, properties in models_kpi.KPIs.items():
        kpi = {} | properties | lts_parser.get_kpi_labels(lts_payload)

        kpi_func = kpi.pop("__func__")
        kpi["value"] = kpi_func(lts_payload)

        kpis[name] = models_lts.NotebookPerformanceKPI.parse_obj(kpi)

    return kpis
