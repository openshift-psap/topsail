import sys
import pathlib

import datasets

PROMPT_DICT = {
    "prompt_input": (
        "Below is an instruction that describes a task, paired with an input that provides further context. "
        "Write a response that appropriately completes the request.\n\n"
        "### Instruction:\n{instruction}\n\n### Input:\n{input}\n\n### Label:"
    ),
    "prompt_no_input": (
        "Below is an instruction that describes a task. "
        "Write a response that appropriately completes the request.\n\n"
        "### Instruction:\n{instruction}\n\n### Label:"
    ),
}

src = pathlib.Path(sys.argv[1])
dest = pathlib.Path(sys.argv[2])

def format_alpaca_fn(example):
    prompt_input, prompt_no_input = PROMPT_DICT['prompt_input'], PROMPT_DICT['prompt_no_input']
    output = prompt_input.format_map(example) if example.get("input", "") != "" else prompt_no_input.format_map(example)
    output = f"{output} {example['output']}"
    return {"output": output}


print(f"Converting {src} ...")
ds = datasets.load_dataset('json', data_files=str(src))

alpaca_ds = ds['train'].map(format_alpaca_fn, remove_columns=['instruction', 'input'])

print(f"Saving into {dest} ...")

alpaca_ds.to_json(dest)
