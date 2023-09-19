#!/usr/bin/env python

import sys, os
import pathlib
import subprocess
import logging
import datetime
import time
import functools

import fire
TESTING_THIS_DIR = pathlib.Path(__file__).absolute().parent
TESTING_UTILS_DIR = TESTING_THIS_DIR.parent / "utils"
PSAP_ODS_SECRET_PATH = pathlib.Path(os.environ.get("PSAP_ODS_SECRET_PATH", "/env/PSAP_ODS_SECRET_PATH/not_set"))
sys.path.append(str(TESTING_THIS_DIR.parent))
from common import env, config, run, visualize

# ---

def consolidate_model(index):
    model_name = config.ci_artifacts.get_config("tests.e2e.models")[index]
    return prepare_scale.consolidate_model_config(_model_name=model_name)

def consolidate_models(use_job_index=False):
    consolidated_models = []
    if use_job_index is not None:
        job_index = os.environ.get("JOB_COMPLETION_INDEX", "0")
        consolidated_models.append(consolidate_model(job_index))
    else:
        for index in len(config.ci_artifacts.get_config("tests.e2e.models")):
            consolidated_models.append(consolidate_model(index))

    config.ci_artifacts.set_config("tests.e2e.consolidated_models", consolidated_models)

# ---

def test():
    "Executes the full e2e test"

    deploy_models()

    run.run(f"./run_toolbox.py from_config local_ci run_multi --suffix test_single")

    run.run(f"./run_toolbox.py from_config local_ci run_multi --suffix test_all")


def deploy_models_sequentially():
    "Deploys all the configured models sequencially (one after the other) -- for local usage"

    logging.info("Deploy the models sequentially")
    consolidated_models()


def deploy_models_concurrently():
    "Deploys all the configured models concurrently (all at the same time)"
    logging.info("Deploy the models concurrently")
    consolidated_models(use_job_index=True)


def test_models_sequencially():
    "Tests all the configured models sequencially (one after the other)"
    logging.info("Test the models sequencially")
    consolidated_models()


def test_models_concurrently():
    "Tests all the configured models concurrently (all at the same time)"
    consolidated_models(use_job_index=True)

# ---

class Entrypoint:
    """
    Commands for launching the CI tests
    """

    def __init__(self):
        self.test_models_sequencially = test_models_sequencially
        self.test_models_concurrently = test_models_concurrently

def main():
    # Print help rather than opening a pager
    fire.core.Display = lambda lines, out: print(*lines, file=out)

    fire.Fire(Entrypoint())


if __name__ == "__main__":
    try:
        from test import init
        init(ignore_secret_path=False, apply_preset_from_pr_args=True)

        sys.exit(main())
    except subprocess.CalledProcessError as e:
        logging.error(f"Command '{e.cmd}' failed --> {e.returncode}")
        sys.exit(1)
    except KeyboardInterrupt:
        print() # empty line after ^C
        logging.error(f"Interrupted.")
        sys.exit(1)
