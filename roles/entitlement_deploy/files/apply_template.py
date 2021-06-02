#!/usr/bin/env python3

import base64
import sys


def main():
    keyname = sys.argv[1]
    value = sys.argv[2]

    if value.startswith("@"):
        filename = value[1:]  # Skip @
        print(
            f"Replacing '{keyname}' with the base64 of the content of '{filename}'",
            file=sys.stderr,
        )

        with open(filename, "rb") as f:
            value = base64.b64encode(f.read()).decode()
    else:
        print(f"Replacing '{keyname}' with '{value}'", file=sys.stderr)

    found = False
    for line in sys.stdin:
        if keyname in line:
            found = True
        print(line.replace(keyname, value), end="")

    exit(0 if found else 1)


if __name__ == "__main__":
    main()
