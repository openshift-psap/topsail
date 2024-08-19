#! /usr/bin/env python

import sys
import pathlib
import statistics as stats
import json
import logging

import convert_dataset_helper

try:
    tokenizer_name = sys.argv[1]
    dataset = pathlib.Path(sys.argv[2])
    max_seq_length = int(sys.argv[3])
except Exception:
    logging.info("Loading from FMS_HF_TUNING configuration ...")
    fms_config = convert_dataset_helper.load_fms_hf_tuning_configuration()

    dataset = fms_config["training_data_path"]
    # tokenizer_name = fms_config["tokenizer_name_or_path"]
    max_seq_length = fms_config["max_seq_length"]

logging.info("Loading the tokenizer ...")
tokenizer = convert_dataset_helper.get_tokenizer(tokenizer_name)
tokenizer_model_max_length = tokenizer.model_max_length

logging.info("Parsing the dataset ...")
token_counts = []
with open(dataset, "r") as f:
    for line in f.readlines():
        data = json.loads(line)
        decoded = tokenizer.encode(data["output"], padding=True)
        sample_token_count = convert_dataset_helper.get_token_count(tokenizer, line)
        actual_token_count = min(sample_token_count, max_seq_length, tokenizer_model_max_length)
        token_counts.append(actual_token_count)

if len(token_counts) < 2:
    logging.warning("Not enough samples found in the dataset ...")
    sys.exit(1)

ds_stats = dict(
    total_tokens = sum(token_counts),
    total_samples = len(token_counts),
    avg_tokens_per_sample = round(stats.mean(token_counts)),
    max_seq_token = max(token_counts),
)

print("dataset stats:", json.dumps(ds_stats).strip())
