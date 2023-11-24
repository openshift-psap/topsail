#! /usr/bin/env python3

import sys, os
import pathlib
import logging
logging.getLogger().setLevel(logging.INFO)

ARTIFACT_DIR = pathlib.Path(os.environ["ARTIFACT_DIR"])

PR_POSITIONAL_ARG_KEY = "PR_POSITIONAL_ARG"

def main():
    old_variable_overrides = {}
    with open(ARTIFACT_DIR / "variable_overrides") as f:
        for line in f.readlines():
            if not line.strip():
                continue

            key, found, value = line.strip().partition("=")
            if not found:
                logging.error(f"Invalid line (no '=') in 'variable_overrides': {line.strip()}")
                continue

            old_variable_overrides[key] = value
    original_variable_overrides = old_variable_overrides.copy()

    try:
        project_name = old_variable_overrides.pop(f"{PR_POSITIONAL_ARG_KEY}_1")
        logging.info(f"Project to run: {project_name}")
    except KeyError:
        logging.fatal(f"The first PR parameter ({PR_POSITIONAL_ARG_KEY}_1) must contain the name of the project to test ...")
        return 1

    new_variable_overrides = {}

    # pass all args without the first arg
    old_all_args = old_variable_overrides.pop(f"{PR_POSITIONAL_ARG_KEY}S")
    new_all_args = old_all_args.partition(" ")[-1]
    new_variable_overrides[f"{PR_POSITIONAL_ARG_KEY}S"] = new_all_args


    # pass the new arg0
    test_name = old_variable_overrides.pop(f"{PR_POSITIONAL_ARG_KEY}_0")
    new_variable_overrides[f"{PR_POSITIONAL_ARG_KEY}_0"] = f"{project_name}-{test_name}"

    # pass all the other values
    for key, value in old_variable_overrides.items():

        # reduce of 1 the positional indexes
        if key.startswith(PR_POSITIONAL_ARG_KEY):
            key_suffix = key.replace(f"{PR_POSITIONAL_ARG_KEY}_", "")
            if key_suffix.isdigit():
                old_positional_idx = int(key_suffix)
                new_positional_idx = old_positional_idx - 1

                new_variable_overrides[f"{PR_POSITIONAL_ARG_KEY}_{new_positional_idx}"] = value
                continue

        # pass untouched everything else
        new_variable_overrides[key] = value


    run_args = " ".join(sys.argv[1:])
    logging.info(f"RHOAI launcher: execute '{project_name}' {run_args}")
    logging.info("New variable overrides:")
    # write the new file
    with open(ARTIFACT_DIR / "variable_overrides", "w") as f:
        for key, value in new_variable_overrides.items():
            print(f"{key}={value}", file=f)
            logging.info(f"{key}={value}")
        print("", file=f)

    with open(ARTIFACT_DIR / "variable_overrides.orig", "w") as f:
        print(f"# original {PR_POSITIONAL_ARG_KEY} values:", file=f)
        for key, value in sorted(original_variable_overrides.items()):
            if not key.startswith(PR_POSITIONAL_ARG_KEY):
                continue
            print(f"{key}={value}", file=f)
    command = f"run {project_name} {run_args}"
    logging.info(f"===> Starting '{command}' <===")

    return os.system(command)





if __name__ == "__main__":
    sys.exit(main())
