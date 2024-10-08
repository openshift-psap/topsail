import types
import pathlib
import logging
import yaml
import os
import json
import datetime
import urllib
import uuid

import pandas as pd

import jsonpath_ng

import matrix_benchmarking.cli_args as cli_args
import matrix_benchmarking.store as store

import projects.matrix_benchmarking.visualizations.helpers.store as helpers_store
import projects.matrix_benchmarking.visualizations.helpers.store.parsers as helpers_store_parsers

register_important_file = None # will be when importing store/__init__.py

K8S_TIME_FMT = "%Y-%m-%dT%H:%M:%SZ"
SHELL_DATE_TIME_FMT = "%a %b %d %H:%M:%S %Z %Y"
ANSIBLE_LOG_DATE_TIME_FMT = "%Y-%m-%d %H:%M:%S"

artifact_dirnames = types.SimpleNamespace()
artifact_paths = types.SimpleNamespace() # will be dynamically populated

IMPORTANT_FILES = [
    "from_rh",
    "fine-tuning.csv",
    "prom.csv",

    "from_ibm",
    "lora_multi_gpu_v.1.2.0.csv",
    "granite-7b-base.csv",
]


def _duplicated_results(import_key, old_entry, old_location, results, location):
    import pdb;pdb.set_trace()
    pass

def parse_always(results, dirname, import_settings):
    # parsed even when reloading from the cache file
    results.test_config = types.SimpleNamespace()
    results.test_config.get = None
    results.test_config.name = None
    results.test_config.yaml_file = None
    pass


def rename_ibm_models(name):
    if name == "granite-20b-v2":
        return "granite-20b-code-base"
    if name == "llama-7b":
        return "llama-2-7b-hf"
    if name == "llama-13b":
        return "llama-2-13b-hf"
    if name == "llama3-8b":
        return "meta-llama-3-8b-instruct"
    return name


RENAME_IBM_KEYS = {
    "gpu_memory_utilization_max": "gpu_memory_usage_max",
    "avg_tokens_per_sample": "tokens_per_sample",
    "number_gpus": "accelerator_count",
    "model_max_length": "max_seq_length",
    "tokens_per_sample": "max_seq_length",
}

def parse_ibm_results(__unused__results, dirname, filename):
    ibm_df = pd.read_csv(register_important_file(dirname, filename))

    ibm_df = ibm_df[ibm_df["is_valid"] != 0]
    ibm_df = ibm_df[ibm_df.method == "lora"]

    ibm_df["orig_model_name"] = ibm_df["model_name"]
    ibm_df.model_name = ibm_df.model_name.apply(rename_ibm_models)

    ibm_df = ibm_df.rename(columns=RENAME_IBM_KEYS)

    settings = {"provider": "IBM"}

    for row_values in ibm_df.values:
        results = types.SimpleNamespace()
        results.data = dict(zip(ibm_df, row_values))

        model_name = results.data["model_name"]
        if "mistral" in model_name: continue
        if not ("llama-2-13b" in model_name.lower() or "granite-20b" in model_name.lower() or "granite-7b"): continue

        for key in "batch_size", "model_name", "max_seq_length", "accelerator_count", "gpu_model":
            value = results.data.pop(key)
            if isinstance(value, float):
                value = int(value)
            settings[key] = value
            results.data[key] = value
        EXIT_CODE = 0

        store.add_to_matrix(settings,
                            pathlib.Path(dirname),
                            results, EXIT_CODE,
                            _duplicated_results)

def parse_rh_results(__unused__results, dirname):
    fms_hf_tuning_df = pd.read_csv(register_important_file(dirname, "fine-tuning.csv"))
    prom_df = pd.read_csv(register_important_file(dirname, "prom.csv"))

    fine_tuning_df = fms_hf_tuning_df.merge(prom_df, on="test_uuid")
    fine_tuning_df.gpu_total_memory_usage_max = fine_tuning_df.gpu_total_memory_usage_max.apply(lambda x: x/1024/1024)

    settings = {"provider": "Red Hat"}

    for row_values in fine_tuning_df.values:
        results = types.SimpleNamespace()
        results.data = dict(zip(fine_tuning_df, row_values))

        model_name = results.data["model_name"]

        for key in "batch_size", "model_name", "max_seq_length", "accelerator_count":
            value = results.data.pop(key)
            if isinstance(value, float):
                value = int(value)
            settings[key] = value
            results.data[key] = value
        settings["gpu_model"] = "NVIDIA-A100-SXM4-80GB"

        EXIT_CODE = 0
        store.add_to_matrix(settings,
                            pathlib.Path(dirname),
                            results, EXIT_CODE,
                            _duplicated_results)



def parse_once(results, dirname):
    if (dirname / "from_ibm").exists():
        parse_ibm_results(results, dirname, "granite-7b-base.csv")
        parse_ibm_results(results, dirname, "lora_multi_gpu_v.1.2.0.csv")
    elif (dirname / "from_rh").exists():
        parse_rh_results(results, dirname)
    else:
        raise ValueError("Unexpected directory:", dirname)
