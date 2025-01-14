#! /usr/bin/python3

import os, sys
import json
import pathlib
import logging
import subprocess

def main():
    config_json_path = os.environ.get("CONFIG_JSON_PATH")
    if not config_json_path:
        logging.fatal("Env var CONFIG_JSON_PATH must point to the config file.")
        return 1

    with open(pathlib.Path(config_json_path)) as f:
        config = json.load(f)

    flavor = config.get("flavor")

    print(f"Running with {flavor}.")

    app_script = pathlib.Path(f"/mnt/app/test_{flavor}.py")

    if not app_script.exists():
        logging.fatal(f"App script for flavor {flavor} doesn't exist :/ ({app_script})")
        return 1

    subprocess.run(f"python3 '{app_script}'", shell=True, check=True)

    return 0


if __name__ == "__main__":
    retcode = main()
    if retcode == 0:
        print("SCRIPT SUCCEEDED")
    else:
        print("SCRIPT FAILED")

    # always exit 0, otherwise the RayJob retries 3 times :/
    sys.exit(0)
