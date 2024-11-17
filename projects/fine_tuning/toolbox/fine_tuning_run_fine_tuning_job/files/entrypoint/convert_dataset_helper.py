from transformers import AutoTokenizer
import logging
import json
import os

logger = logging.getLogger("sft_trainer")

def load_fms_hf_tuning_configuration():
    config_file = os.environ.get("CONFIG_JSON_PATH")
    if not config_file:
        logging.warn("No CONFIG_JSON_PATH available...")
        return {}

    with open(config_file) as f:
        config = json.load(f)

    return config


def get_tokenizer(path_model):
    tokenizer = AutoTokenizer.from_pretrained(path_model)

    special_tokens_dict = dict()

    DEFAULT_PAD_TOKEN = "<PAD>"
    DEFAULT_EOS_TOKEN = "</s>"
    DEFAULT_BOS_TOKEN = "<s>"
    DEFAULT_UNK_TOKEN = "<unk>"

    if tokenizer.pad_token is None:
        logger.warning("PAD token set to default, missing in tokenizer")
        special_tokens_dict["pad_token"] = DEFAULT_PAD_TOKEN
    if tokenizer.eos_token is None:
        logger.warning("EOS token set to default, missing in tokenizer")
        special_tokens_dict["eos_token"] = DEFAULT_EOS_TOKEN
    if tokenizer.bos_token is None:
        logger.warning("BOS token set to default, missing in tokenizer")
        special_tokens_dict["bos_token"] = DEFAULT_BOS_TOKEN
    if tokenizer.unk_token is None:
        logger.warning("UNK token set to default, missing in tokenizer")
        special_tokens_dict["unk_token"] = DEFAULT_UNK_TOKEN

    tokenizer.add_special_tokens(special_tokens_dict)

    return tokenizer


def get_tokens(tokenizer, line):
    data = json.loads(line)
    decoded = tokenizer.encode(data["output"], padding=True)

    return decoded


def get_token_count(tokenizer, line):
    return len(get_tokens(tokenizer, line))
