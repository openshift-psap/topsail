#! /usr/bin/env python

import sys
import pathlib

import convert_dataset_helper

fms_config = convert_dataset_helper.load_fms_hf_tuning_configuration()

max_seq_length = fms_config["max_seq_length"]
tokenizer = convert_dataset_helper.get_tokenizer(fms_config["model_name_or_path"])

src = pathlib.Path(sys.argv[1])
dst = pathlib.Path(sys.argv[2])
FACTOR = float(sys.argv[3])

print(f"Replicating {src} with a factor of {FACTOR}...")
print(f"Filtering out samples with more than {max_seq_length=} tokens")

with open(src) as src_f:
    orig_length = len(src_f.readlines())
    print(f"Length of {src}: {orig_length} lines")

dst.unlink(missing_ok=True)

factor = FACTOR
samples_too_long = 0
while factor >= 1:
    print(f"Saving 1x {src} ...")
    with open(src) as src_f, open(dst, "a") as dst_f:
        for line in src_f.readlines():
            if convert_dataset_helper.get_token_count(tokenizer, line) > max_seq_length:
                if factor == FACTOR: # count them only once
                    samples_too_long += 1
                continue
            print(line.strip(), file=dst_f)

    factor -= 1

    with open(dst) as dst_f:
        new_length = len(dst_f.readlines())
        print(f"Length of {dst}: {new_length} lines")

if 0 < factor < 1:
    newline_count = int(orig_length * factor)

    print(f"Saving {factor}x {src}: {newline_count}/{orig_length} lines ...")

    with open(src) as src_f:
        with open(dst, "a") as dst_f:
            lines = 0
            while lines < newline_count:
                line = src_f.readline()

                if convert_dataset_helper.get_token_count(tokenizer, line) > max_seq_length:
                    if factor == FACTOR: # count them only once
                        samples_too_long += 1
                    continue

                print(line.strip(), file=dst_f)
                lines += 1


with open(dst) as dst_f:
    new_length = len(dst_f.readlines())


print(f"Length of {dst}: {new_length} lines")
print(f"Removed {samples_too_long} samples longer than {max_seq_length=} tokens.")
