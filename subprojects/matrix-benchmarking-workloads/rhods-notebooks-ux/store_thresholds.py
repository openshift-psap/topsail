import pathlib
import types
import yaml
from collections import defaultdict
import logging
import os

thresholds_cache = None

def _parse_thresholds():
    global thresholds_cache
    if thresholds_cache is not None: return

    thresholds_cache = []

    filename = os.environ.get("MATBENCH_RHODS_NOTEBOOKS_UX_CONFIG")
    if not filename:
        logging.info("MATBENCH_RHODS_NOTEBOOKS_UX_CONFIG not set, not loading any threshold.")
        return

    fname = pathlib.Path(__file__).parent / "data" / filename
    with open(fname) as f:
        data = yaml.safe_load(f)

    for entry in data["visualize"]["thresholds"]:
        thresholds_cache.append([entry["settings_selector"], entry["thresholds"]])


def get_thresholds(entry_settings):
    _parse_thresholds()

    entry_thresholds = {}

    for threshold_settings, threshold_values in thresholds_cache:
        for threshold_setting_key, threshold_setting_value in threshold_settings.items():
            if not str(entry_settings.get(threshold_setting_key)) == threshold_setting_value:
                break
        else: # no incompatible settings found, save the threshold
            entry_thresholds.update(threshold_values)

    return entry_thresholds
