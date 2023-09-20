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
import prepare_scale

# ---

def consolidate_model(index):
    model_name = config.ci_artifacts.get_config("tests.e2e.models")[index]
    return prepare_scale.consolidate_model_config(_model_name=model_name)

def consolidate_models(use_job_index=False):
    consolidated_models = []
    if use_job_index:
        job_index = os.environ.get("JOB_COMPLETION_INDEX", None)
        if job_index is None:
            job_index = 0
            logging.warning("No JOB_COMPLETION_INDEX env var. Using {job_index}.")
        job_index = int(job_index)
        consolidated_models.append(consolidate_model(job_index))
    else:
        for index in range(len(config.ci_artifacts.get_config("tests.e2e.models"))):
            consolidated_models.append(consolidate_model(index))

    config.ci_artifacts.set_config("tests.e2e.consolidated_models", consolidated_models)

# ---

def test():
    "Executes the full e2e test"

    run.run(f"./run_toolbox.py from_config local_ci run_multi --suffix deploy_concurrently")

    run.run(f"./run_toolbox.py from_config local_ci run_multi --suffix test_sequencially")

    run.run(f"./run_toolbox.py from_config local_ci run_multi --suffix test_concurrently")


def deploy_models_sequentially():
    "Deploys all the configured models sequencially (one after the other) -- for local usage"

    logging.info("Deploy the models sequentially")
    consolidate_models()
    deploy_consolidated_models()


def deploy_models_concurrently():
    "Deploys all the configured models concurrently (all at the same time)"

    logging.info("Deploy the models concurrently")
    consolidate_models(use_job_index=True)
    deploy_consolidated_models()


def test_models_sequencially():
    "Tests all the configured models sequencially (one after the other)"

    logging.info("Test the models sequencially")
    consolidate_models()
    test_consolidated_models()


def test_models_concurrently():
    "Tests all the configured models concurrently (all at the same time)"

    logging.info("Test the models concurrently")
    consolidate_models(use_job_index=True)
    test_consolidated_models()

# ---

def deploy_consolidated_models():
    consolidated_models = config.ci_artifacts.get_config("tests.e2e.consolidated_models")
    model_count = len(consolidated_models)
    logging.info(f"Found {model_count} models to deploy")
    for consolidated_model in consolidated_models:
        deploy_consolidated_model(consolidated_model)


def deploy_consolidated_model(consolidated_model):
    logging.info(f"Deploying model '{consolidated_model['name']}'")
    pass

def test_consolidated_models():
    consolidated_models = config.ci_artifacts.get_config("tests.e2e.consolidated_models")
    model_count = len(consolidated_models)
    logging.info(f"Found {model_count} models to test")
    for consolidated_model in consolidated_models:
        test_consolidated_model(consolidated_models)

def test_consolidated_model(test_consolidated_model):
    logging.info(f"Testing model '{consolidated_model['name']}")

    pass

# ---

class Entrypoint:
    """
    Commands for launching the CI tests
    """

    def __init__(self):
        self.deploy_models_sequentially = deploy_models_sequentially
        self.deploy_models_concurrently = deploy_models_concurrently
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
