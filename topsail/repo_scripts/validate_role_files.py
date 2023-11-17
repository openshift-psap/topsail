#! /usr/bin/env python

# This script ensures that all the Ansible variables defining a
# filepath (`roles/`) do point to an existing file.

import os
import sys
import yaml
import pathlib

THIS_DIR = pathlib.Path(__file__).absolute().parent
TOP_DIR = THIS_DIR.parent.parent
# go to top directory
os.chdir(TOP_DIR)

ROLES_VARS_GLOB = "roles/*/*/vars/*/*"
FILE_PREFIX = "roles/"

def validate_role_vars_files(yaml_doc):
    errors = 0

    for key, value in yaml_doc.items():
        try:
            if not value.startswith(FILE_PREFIX):
                print()
                print(f"{key}: {value} --> not starting with '{FILE_PREFIX}', ignoring.")
                continue
        except AttributeError: # value.startswith
            print()
            print(f"{key}:{value} --> not a string ({value.__class__.__name__}), ignoring.")
            continue

        if not pathlib.Path(value).exists():
            errors += 1
            print()
            print(f"ERROR: {key}: {value} --> not found")
            continue

        # file found, nothing to do

    return errors

def traverse_role_vars():
    errors = 0
    for filename in TOP_DIR.glob(ROLES_VARS_GLOB):
        msg = ["", f"### {filename.relative_to(TOP_DIR)}"]

        with open(filename) as f:
            try:
                yaml_doc = yaml.safe_load(f)
            except yaml.YAMLError as e:
                msg.append(f"--> invalid YAML file ({e})")
                continue

        if yaml_doc is None:
            msg.append(f"--> empty file")
            continue

        file_errors = validate_role_vars_files(yaml_doc)
        errors += file_errors

        msg.append(f"--> found {file_errors} error{'s' if file_errors > 1 else ''} in {filename.relative_to(TOP_DIR)}")
        if file_errors:
            print("\n".join(msg))

    return errors

def main():
    if "-h" in sys.argv or "--help" in sys.argv:
        print("""\
This script ensures that all the Ansible variables defining a
filepath (`roles/`) do point to an existing file.""")
        return 0

    print(f"INFO: Searching for missing files in '{ROLES_VARS_GLOB}'")
    errors = traverse_role_vars()

    print()
    print(f"{'ERROR' if errors else 'INFO'}: found {errors} missing file{'s' if errors > 1 else ''}")

    return 1 if errors else 0

if __name__ == "__main__":
    exit(main())
