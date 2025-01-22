import types
import datetime
import logging
import pytz
import json
import functools

import matrix_benchmarking.common as common
from matrix_benchmarking.parse import json_dumper

from . import models, lts_parser


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
        models.NotebookScalePayload.parse_obj(parsed_lts)
        return True

    except Exception as e:
        logging.error(f"lts-error: Failed to validate the generated LTS payload against the model")
        logging.error(f"lts-error: entry settings: {import_settings}")

        if reraise:
            raise

        logging.error(f"lts-error: validation issue(s): {e}")

        return False

