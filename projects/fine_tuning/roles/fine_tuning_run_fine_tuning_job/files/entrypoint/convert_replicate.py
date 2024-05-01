#! /usr/bin/env python

import sys
import pathlib

src = pathlib.Path(sys.argv[1])
dst = pathlib.Path(sys.argv[2])
FACTOR = float(sys.argv[3])

print(f"Replicating {src} with a factor of {FACTOR}...")

with open(src) as src_f:
    orig_length = len(src_f.readlines())
    print(f"Length of {src}: {orig_length} lines")

dst.unlink(missing_ok=True)

factor = FACTOR

while factor >= 1:
    print(f"Saving 1x {src} ...")
    with open(src) as src_f, open(dst, "a") as dst_f:
        for line in src_f.readlines():
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
            for _ in range(newline_count):
                print(src_f.readline().strip(), file=dst_f)

with open(dst) as dst_f:
    new_length = len(dst_f.readlines())
    print(f"Length of {dst}: {new_length} lines")
