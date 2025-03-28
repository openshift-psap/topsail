#! /usr/bin/env python3

import sys, os
import pathlib
import logging
logging.getLogger().setLevel(logging.INFO)
import yaml

ARTIFACT_DIR = pathlib.Path(os.environ.get("ARTIFACT_DIR", "."))

PR_POSITIONAL_ARG_KEY = "PR_POSITIONAL_ARG"

RHOAI_CONFIG_KEY = "_rhoai_."
rhoai_configuration = {
    "subproject": None, # _rhoai_.subproject allows overriding the subproject received as sys.argv[1]
}

def main():
    old_variable_overrides = {}
    variable_overrides_path = ARTIFACT_DIR / "variable_overrides.yaml"
    if not variable_overrides_path.exists():
        logging.fatal(f"File {variable_overrides_path.absolute()} does not exist. Cannot proceed.")
        raise SystemExit(1)

    with open(variable_overrides_path) as f:
        old_variable_overrides = yaml.safe_load(f)

    if not isinstance(old_variable_overrides, dict):
        logging.fatal(f"Wrong type for the variable overrides file. Expected a dictionnary, got {old_variable_overrides.__class__.__name__}")
        raise SystemExit(1)

    for key, value in old_variable_overrides.items():
        _, found, new_key = key.partition(RHOAI_CONFIG_KEY)
        if not found:
            continue

        logging.info(f"RHOAI launcher configuration: {new_key} --> {value}")

        if new_key not in rhoai_configuration:
            logging.fatal(f"{new_key} is an invalid RHOAI launch configuration key. Expected one of [{', '.join(rhoai_configuration.keys())}]")
            raise SystemExit(1)

        rhoai_configuration[new_key] = value


    original_variable_overrides = old_variable_overrides.copy()

    new_variable_overrides = {}

    # pass all args ...
    old_all_args = old_variable_overrides.pop(f"{PR_POSITIONAL_ARG_KEY}S", "").strip("'").split()
    if old_all_args and old_all_args[0].startswith("perf-ci"):
        perflab_test_name = old_all_args.pop(0)
        logging.info(f"Perflab test name: {perflab_test_name}")

    new_all_args = []
    for idx, arg in enumerate(old_all_args):
        # ... without the arg0 and arg1
        if idx == 0: continue

        # ... without RHOAI config flags
        rhoai_conf = False
        for key in rhoai_configuration.keys():
            _, found, value = arg.partition(f"{key}=")
            if not found: continue
            logging.info(f"RHOAI launcher: setting {RHOAI_CONFIG_KEY}{key}={value} from the test args.")
            rhoai_configuration[key] = value
            rhoai_conf = True
            break
        if rhoai_conf: continue
        # ... arg can be passed
        new_all_args.append(arg)

    # generate the new arg0
    try:
        test_name = old_variable_overrides[f"{PR_POSITIONAL_ARG_KEY}_0"]
    except KeyError:
        logging.fatal(f"RHOAI launcher: the 0th PR parameter ({PR_POSITIONAL_ARG_KEY}_0) must contain the test name ...")
        raise SystemExit(1)

    try:
        project_name = old_all_args[0]
        logging.info(f"RHOAI launcher: project to run: {project_name}")
    except IndexError:
        logging.fatal(f"RHOAI launcher: the first PR parameter ({PR_POSITIONAL_ARG_KEY}_1) must contain the name of the project to test ...")
        return 1

    # ---

    new_variable_overrides[f"{PR_POSITIONAL_ARG_KEY}S"] = " ".join(new_all_args)

    all_args_arg0 = f"{project_name}-{test_name}"
    if subproject := rhoai_configuration["subproject"]:
        all_args_arg0 = f"{subproject}-{all_args_arg0}"

    for idx, arg in enumerate([all_args_arg0] + new_all_args):
        new_variable_overrides[f"{PR_POSITIONAL_ARG_KEY}_{idx}"] = arg

    # pass all the other values
    for key, value in old_variable_overrides.items():
        # reduce of 1 the positional indexes
        if key.startswith(PR_POSITIONAL_ARG_KEY) and \
           (key_suffix := key.replace(f"{PR_POSITIONAL_ARG_KEY}_", "")).isdigit():
            continue

        # skip rhoai-entrypoint config variables
        if key.startswith(RHOAI_CONFIG_KEY):
            continue

        # pass untouched everything else
        new_variable_overrides[key] = value

    run_argv = sys.argv[1:]

    if subproject := rhoai_configuration["subproject"]:
        run_argv[0] = subproject

    run_args = " ".join(run_argv)
    logging.info(f"RHOAI launcher: execute: {project_name} {run_args}")
    logging.info("New variable overrides:")
    # write the new file
    with open(ARTIFACT_DIR / "variable_overrides.yaml", "w") as f:
        print(f"# RHOAI: run {project_name} {run_args}", file=f)
        for key, value in new_variable_overrides.items():
            if key.startswith(RHOAI_CONFIG_KEY):
                continue

            logging.info(f"{key}={value}")

        yaml.dump(new_variable_overrides, f)

    with open(ARTIFACT_DIR / "variable_overrides.yaml.orig", "w") as f:
        yaml.dump(old_variable_overrides, f)

    command = f"run {project_name} {run_args}"
    logging.info(f"===> Starting '{command}' <===")

    return os.WEXITSTATUS(os.system(command))


if __name__ == "__main__":
    sys.exit(main())
