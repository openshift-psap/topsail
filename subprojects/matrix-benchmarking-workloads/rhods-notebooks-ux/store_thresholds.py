import pathlib
import types
import csv
from collections import defaultdict

thresholds_cache = None

def _parse_thresholds():
    global thresholds_cache
    if thresholds_cache is not None: return

    thresholds_cache = []
    data = []
    for fname in (pathlib.Path(__file__).parent / "data").glob("*.thresholds"):
        with open(fname) as f:
            data += [row for row in csv.reader(f)]

    for properties in data:
        threshold_settings = {}
        threshold_values = {}
        thresholds_cache.append([threshold_settings, threshold_values])

        current_bucket = threshold_settings

        for _prop in properties:
            prop = _prop.strip()

            if prop == "*":
                current_bucket = threshold_values
                continue

            prop_key, _, prop_value = prop.partition("=")
            current_bucket[prop_key] = prop_value

        if not threshold_values:
            raise ValueError(f"Found no threshold value in '{row}'")


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
