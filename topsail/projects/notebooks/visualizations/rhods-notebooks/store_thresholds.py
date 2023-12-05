import pathlib
import types
import yaml
from collections import defaultdict
import logging
import os, sys

thresholds_cache = None

def _parse_thresholds():
    global thresholds_cache
    if thresholds_cache is not None: return

    thresholds_cache = []

    filename = os.environ.get("MATBENCH_RHODS_NOTEBOOKS_UX_CONFIG")
    if not filename:
        logging.info("MATBENCH_RHODS_NOTEBOOKS_UX_CONFIG not set, not loading any threshold.")
        return
    config_id = os.environ.get("MATBENCH_RHODS_NOTEBOOKS_UX_CONFIG_ID")

    fname = pathlib.Path(__file__).parent / "data" / filename
    with open(fname) as f:
        data = yaml.safe_load(f)

    if len(data["visualize"]) > 1 and not config_id:
        logging.error(f"Found {len(data['visualize'])} 'visualize' items in {filename} and MATBENCH_RHODS_NOTEBOOKS_UX_CONFIG_ID not set.")
        sys.exit(1)

    for visualization in data["visualize"]:
        if config_id and visualization["id"] != config_id:
            continue

        for threshold in visualization.get("thresholds", []):
            if "files" not in threshold:
                # threshold entry is here, cache it
                thresholds_cache.append([threshold["settings_selector"] or {}, threshold["thresholds"] or {}])
                continue

            for filename in threshold["files"]:
                # threshold entries are in another file, process it
                with open(fname.parent / filename) as f:
                    threshold_file_data = yaml.safe_load(f)
                    for threshold_file_entry in threshold_file_data:
                        thresholds_cache.append(
                            [threshold_file_entry["settings_selector"] or {},
                             threshold_file_entry["thresholds"] or {}])

    if not thresholds_cache:
        logging.info(f"No threshold found in {filename}|{config_id}.")

def get_thresholds(entry_settings):
    _parse_thresholds()

    entry_thresholds = {}

    for threshold_settings, threshold_values in thresholds_cache:
        for threshold_setting_key, threshold_setting_value in threshold_settings.items():
            if not str(entry_settings.get(threshold_setting_key)) == str(threshold_setting_value):
                break
        else: # no incompatible settings found, save the threshold
            entry_thresholds.update(threshold_values)

    return entry_thresholds
