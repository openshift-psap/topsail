#! /usr/bin/env python

# This script ensures that all the Ansible variables defined are
# actually used in their role (with an exception for symlinks)

import os
import sys
import yaml
import subprocess
import pathlib
import itertools
import shlex

THIS_DIR = pathlib.Path(__file__).absolute().parent
TOP_DIR = THIS_DIR.parent.parent
# go to top directory
os.chdir(TOP_DIR)

ROLES_VARS_GLOB = "roles/*/vars/*/*"
ROLES_DEFAULTS_GLOB = "roles/*/defaults/*/*"

def validate_role_vars_used(filename, yaml_doc):
    errors = 0

    # filename.parts[len(TOP_DIR.parts)] is 'roles'
    role_name = filename.parts[len(TOP_DIR.parts)+1]
    for key in yaml_doc:
        grep_command = ["grep", key,
                        str(pathlib.Path("roles") / role_name),
                        "--recursive",
                        ]
        proc = subprocess.run(grep_command, capture_output=True)

        if proc.returncode != 0:
            print("DEBUG:", shlex.join(grep_command))
            # grep should always find 'key' inside 'filename',
            # I couldn't find how to exclude one specific file with
            # grep options....
            print(proc.stderr)
            print("ERROR: grep shouldn't have failed ...")
            proc.check_returncode() # raises a subprocess.CalledProcessError

        count = len(proc.stdout.decode('utf-8').splitlines())
        count -= 1 # exclude 'key' found inside 'filename'
        if count == 0:
            print(f"ERROR: '{key}' not used in role '{role_name}'")
            errors += 1
            continue

        # key is used, nothing to do

    return errors

def traverse_role_vars_defaults():
    errors = 0
    for filename in itertools.chain(TOP_DIR.glob(ROLES_VARS_GLOB), TOP_DIR.glob(ROLES_DEFAULTS_GLOB)):
        print()

        print("###", filename.relative_to(TOP_DIR))

        if filename.is_symlink():
            print(f"--> is a symlink, don't check.")
            continue

        with open(filename) as f:
            try:
                yaml_doc = yaml.safe_load(f)
            except yaml.YAMLError as e:
                print(f"--> invalid YAML file ({e})")
                continue

        if yaml_doc is None:
            print(f"--> empty file")
            continue

        file_errors = validate_role_vars_used(filename, yaml_doc)
        errors += file_errors

        print(f"--> found {file_errors} error{'s' if file_errors > 1 else ''} in {filename.relative_to(TOP_DIR)}")

    return errors

def main():
    if "-h" in sys.argv or "--help" in sys.argv:
        print("""\
This script ensures that all the Ansible variables defined are
actually used in their role (with an exception for symlinks)""")
        return 0

    print(f"INFO: Searching for used variables in '{ROLES_VARS_GLOB}'")
    errors = traverse_role_vars_defaults()

    print()
    print(f"{'ERROR' if errors else 'INFO'}: found {errors} unused variable{'s' if errors > 1 else ''}")

    return 1 if errors else 0

if __name__ == "__main__":
    exit(main())
