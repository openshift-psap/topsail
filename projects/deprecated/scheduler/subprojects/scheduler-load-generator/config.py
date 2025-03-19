import yaml
import jsonpath_ng
import pathlib
import os
import logging
import json

ARTIFACT_DIR = pathlib.Path(os.environ.get("ARTIFACT_DIR", "."))

main_config = None

def load_config():
    global main_config


    job_templates = {}
    main_config = dict(job_templates=job_templates)

    for fname in (pathlib.Path(__file__).parent / "templates").glob("*.yaml"):
        with open(fname) as f:
            job_templates[fname.stem] = yaml.safe_load(f)

    return main_config


def get_config(jsonpath, config=None):
    if config is None:
        config = main_config

    try:
        return jsonpath_ng.parse(jsonpath).find(config)[0].value
    except IndexError:
        raise IndexError(f"Couldn't find {jsonpath} key ...")


def set_config(config, jsonpath, value):
    jsonpath_ng.parse(jsonpath).update_or_create(config, value)
