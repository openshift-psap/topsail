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
import logging
logging.getLogger().setLevel(logging.INFO)

SCRIPT_THIS_DIR = pathlib.Path(__file__).absolute().parent
TOPSAIL_DIR = SCRIPT_THIS_DIR.parent.parent.parent

TOPSAIL_ROLES_GLOB = "projects/*/toolbox/*"

ROLE_VARS_GLOB = "vars/*/*"
ROLE_DEFAULTS_GLOB = "defaults/*/*"

def validate_role_vars_used(dirname, filename, yaml_doc):
    errors = []
    messages = []
    # filename.parts[len(TOPDIR_DIR.parts)] is 'roles'
    successes = 0
    role_name = dirname.name
    for key in yaml_doc:
        if key == "__safe": continue

        grep_command = ["grep", key, dirname,
                        "--dereference-recursive"]

        proc = subprocess.run(grep_command, capture_output=True)

        if proc.returncode != 0:
            logging.debug(str(shlex.join(grep_command)))
            # grep should always find 'key' inside 'filename',
            # I couldn't find how to exclude one specific file with
            # grep options....
            logging.info(str(proc.stderr))
            logging.fatal("grep shouldn't have failed ...")
            proc.check_returncode() # raises a subprocess.CalledProcessError

        count = len(proc.stdout.decode('utf-8').splitlines())
        count -= 1 # exclude 'key' found inside 'filename'
        if count == 0:
            errors.append(f"'{key}' not used in role '{role_name}'")
            continue

        successes += 1

    return errors, messages, successes


def traverse_files(dirname):
    logging.debug(f"Searching for unused variables in '{dirname}'")

    errors = 0
    successes = 0

    for filename in itertools.chain(dirname.glob(ROLE_VARS_GLOB), dirname.glob(ROLE_DEFAULTS_GLOB)):
        successes += 1

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
        while dirname.name not in ("vars", "defaults"):
            dirname = dirname.parent
        dirname = dirname.parent

        file_errors, messages, succ = validate_role_vars_used(dirname, filename, yaml_doc)
        errors += len(file_errors)
        successes += succ

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

    return errors, successes


def traverse_roles():
    errors = 0
    successes = 0
    for dirname in TOPSAIL_DIR.glob(TOPSAIL_ROLES_GLOB):
        logging.debug("")
        err, succ = traverse_files(dirname)

        errors += err
        successes += succ

    return errors, successes


def main():
    if "-h" in sys.argv or "--help" in sys.argv:
        logging.info("""\
This script ensures that all the Ansible variables defined are
actually used in their role (with an exception for symlinks)""")
        return 0

    errors, successes = traverse_roles()

    logging.debug("")
    if errors:
        logging.fatal(f"Found {errors} unused variable{'s' if errors > 1 else ''}")
        return 1

    if successes == 0:
        logging.fatal(f"Didn't traverse any file :/")
        return 1

    logging.info(f"{successes} files have been validated.")
    logging.info("All good :)")
    return 0


if __name__ == "__main__":
    exit(main())
