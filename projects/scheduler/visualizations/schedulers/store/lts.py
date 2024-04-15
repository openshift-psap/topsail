import logging
import types
import json
import functools
import uuid

import matrix_benchmarking.common as common
from matrix_benchmarking.parse import json_dumper

from .. import models
from ..models import lts as models_lts


def validate_lts_payload(lts_payload):
    json_lts = json.dumps(lts_payload, indent=4, default=functools.partial(json_dumper, strict=False))

    parsed_lts = json.loads(json_lts)
    try:
        models.lts.Payload.parse_obj(parsed_lts)
        return True

    except Exception as e:
        logging.error(f"lts-error: Failed to validate the generated LTS payload against the model: {e}")
        return False


def build_lts_payloads():
    for entry in common.Matrix.processed_map.values():
        results = entry.results

        start_time = results.test_start_end_time.start
        end_time = results.test_start_end_time.end

        lts_payload = results.lts

        validate_lts_payload(lts_payload)

        yield lts_payload, start_time, end_time


def _gather_prom_metrics(metrics, model) -> dict:
    data = {metric_name: metrics[metric_name]
            for metric_name in model.schema()["properties"].keys()}

    return model(**data)
