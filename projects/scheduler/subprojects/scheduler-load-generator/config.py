import yaml
import jsonpath_ng
import pathlib
import os
import logging
import json

ARTIFACT_DIR = pathlib.Path(os.environ.get("ARTIFACT_DIR", "."))

with open(pathlib.Path(__file__).parent / "config.yaml") as f:
    main_config = yaml.safe_load(f)

def get_config(jsonpath, config=main_config):
    return jsonpath_ng.parse(jsonpath).find(config)[0].value


def set_config(config, jsonpath, value):
    get_config(jsonpath, config=config) # will raise an exception if the jsonpath does not exist
    jsonpath_ng.parse(jsonpath).update(config, value)
