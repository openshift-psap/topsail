#! /usr/bin/env python

# This script ensures that all the Ansible variables defining a
# filepath (`roles/`) do point to an existing file.

import os
import sys
import yaml
import pathlib
import logging
logging.getLogger().setLevel(logging.INFO)

SCRIPT_THIS_DIR = pathlib.Path(__file__).absolute().parent
TOPSAIL_DIR = SCRIPT_THIS_DIR.parent.parent.parent

ROLES_VARS_GLOB = "projects/*/roles/*/vars/*/*"
FILE_PREFIX = "roles/"

def validate_role_vars_files(dirname, yaml_doc):
    errors = []
    messages = []
    for key, value in yaml_doc.items():
        if not isinstance(value, str):
            messages.append(f"{key}:{value} --> not a string ({value.__class__.__name__}), ignoring.")
            continue

        if (dirname / value).exists():
            # file exists inside the role, continue
            continue

        if (TOPSAIL_DIR / value).exists():
            # file exists in topsail topdir, continue
            continue

        if value.startswith("/"):
            messages.append(f"{key}:{value} --> absolute path, ignoring")
            continue

        if not "/" in value and not "." in value:
            messages.append(f"{key}:{value} --> likely not a path, ignoring")
            continue

        errors.append(f"{key}: {value} --> not found")
        continue

    return errors, messages

def traverse_role_vars():
    errors = 0
    successes = 0
    for filename in TOPSAIL_DIR.glob(ROLES_VARS_GLOB):

        with open(filename) as f:
            try:
                yaml_doc = yaml.safe_load(f)
            except yaml.YAMLError as e:
                logging.warning(f"{filename} --> invalid YAML file ({e})")
                continue
            except Exception as e:
                logging.warning(f"{filename} --> invalid YAML file ({e})")
                errors += 1

        if yaml_doc is None:
            continue
            logging.warning(f"{filename} --> empty file)")
            continue

        dirname = filename.parent
        while dirname.name != "vars":
            dirname = dirname.parent
        dirname = dirname.parent

        file_errors, messages = validate_role_vars_files(dirname, yaml_doc)
        errors += len(file_errors)

        if not file_errors:
            successes += 1

        if not file_errors and not messages:
            continue

        logging.info(f"### {filename.relative_to(TOPSAIL_DIR)}")

        for msg in file_errors:
            logging.error(msg)
        if file_errors:
            logging.warning(f"--> found {len(file_errors)} error{'s' if len(file_errors) > 1 else ''} in {filename.relative_to(TOPSAIL_DIR)}")
        for msg in messages:
            logging.info(msg)

        logging.info("\n")

    return successes, errors


def main():
    if "-h" in sys.argv or "--help" in sys.argv:
        logging.info("""\
This script ensures that all the Ansible variables defining a
filepath (`roles/`) do point to an existing file.""")
        return 0

    logging.info(f"Searching for missing files in '{ROLES_VARS_GLOB}'")
    successes, errors = traverse_role_vars()

    if errors:
        logging.fatal(f"Found {errors} missing file{'s' if errors > 1 else ''}")
        return 1


    if successes == 0:
        logging.fatal(f"Found no role file :/")
        logging.info(f"Search pattern: {ROLES_VARS_GLOB}")

        return 1

    logging.info("All good :)")
    return 0

if __name__ == "__main__":
    exit(main())
