#! /usr/bin/python3

import fileinput
import base64
import sys

template = sys.argv[1]
keyname = sys.argv[2]
filename = sys.argv[3]
print(f"Replacing '{keyname}' with the content of '{filename}'", file=sys.stderr)

with open(filename, "rb") as f:
    file_b64 = base64.b64encode(f.read()).decode()

found = False
for line in fileinput.input(files=[template]):
    if keyname in line: found = True
    print(line.replace(keyname, file_b64), end="")
exit(0 if found else 1)
