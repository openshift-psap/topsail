#!/usr/bin/env python

import sys, os
import pathlib
import subprocess
import logging
logging.getLogger().setLevel(logging.INFO)
import functools

import fire

from projects.core.library import env, config
from projects.matrix_benchmarking.library import visualize

import prepare_mcad, test_mcad
import prepare_sdk_user, test_sdk_user

TESTING_THIS_DIR = pathlib.Path(__file__).absolute().parent

PSAP_ODS_SECRET_PATH = pathlib.Path(os.environ.get("PSAP_ODS_SECRET_PATH", "/env/PSAP_ODS_SECRET_PATH/not_set"))
LIGHT_PROFILE = "light"

initialized = False
def init(ignore_secret_path=False, apply_preset_from_pr_args=True):
    global initialized
    if initialized:
        logging.debug("Already initialized.")
        return
    initialized = True

    env.init()
    config.init(TESTING_THIS_DIR)

    if apply_preset_from_pr_args:
        config.ci_artifacts.apply_preset_from_pr_args()

    if not ignore_secret_path and not PSAP_ODS_SECRET_PATH.exists():
        raise RuntimeError("Path with the secrets (PSAP_ODS_SECRET_PATH={PSAP_ODS_SECRET_PATH}) does not exists.")


    config.ci_artifacts.detect_apply_light_profile(LIGHT_PROFILE)


def entrypoint(ignore_secret_path=False, apply_preset_from_pr_args=True):
    def decorator(fct):
        @functools.wraps(fct)
        def wrapper(*args, **kwargs):
            init(ignore_secret_path, apply_preset_from_pr_args)
            fct(*args, **kwargs)

        return wrapper
    return decorator

# ---

@entrypoint()
def test_ci():
    """
        Runs the test from the CI
    """

    test_mode = config.ci_artifacts.get_config("tests.mode")
    if test_mode == "mcad":
        return test_mcad.test()
    elif test_mode == "sdk_user":
        return test_sdk_user.test()
    else:
        raise KeyError(f"Invalid test mode: {test_mode}")


@entrypoint()
def mcad_test(name=None, dry_mode=None, visualize=None, capture_prom=None, prepare_nodes=None):
    """
    Runs the test from the CI

    Args:
      name: name of the test to run. If empty, run all the tests of the configuration file
      dry_mode: if True, do not execute the tests, only list what would be executed
      visualize: if False, do not generate the visualization reports
      capture_prom: if False, do not capture Prometheus database
      prepare_nodes: if False, do not scale up the cluster nodes
    """

    test_mcad.test(name, dry_mode, visualize, capture_prom, prepare_nodes)

# ---

@entrypoint(ignore_secret_path=True, apply_preset_from_pr_args=False)
def generate_plots_from_pr_args():
    """
    Generates the visualization reports from the PR arguments
    """

    visualize.download_and_generate_visualizations()


@entrypoint(ignore_secret_path=True)
def generate_plots(results_dirname):
    visualize.generate_from_dir(results_dirname)

# ---

@entrypoint()
def prepare_ci():
    """
    Prepares the cluster and the namespace for running the tests
    """

    test_mode = config.ci_artifacts.get_config("tests.mode")
    if test_mode == "mcad":
        prepare_mcad.prepare()
    elif test_mode == "sdk_user":
        return prepare_sdk_user.prepare()
    else:
        raise KeyError(f"Invalid test mode: {test_mode}")


@entrypoint()
def cleanup_cluster():
    """
    Restores the cluster to its original state
    """

    test_mode = config.ci_artifacts.get_config("tests.mode")
    if test_mode == "mcad":
        return prepare_mcad.cleanup_cluster()
    elif test_mode == "sdk_user":
        return prepare_sdk_user.cleanup_cluster()
    else:
        raise KeyError(f"Invalid test mode: {test_mode}")


@entrypoint()
def mcad_run_one_matbench():
    """
    Runs one MCAD test as part of a MatrixBenchmark benchmark
    """

    test_mcad.run_one_matbench()


@entrypoint()
def sdk_user_run_one():
    """
    Runs one codeflare SDK user test
    """

    test_sdk_user.run_one()

# ---

class Entrypoint:
    """
    Commands for launching the CI tests
    """

    def __init__(self):
        self.cleanup_cluster_ci = cleanup_cluster

        self.prepare_ci = prepare_ci
        self.test_ci = test_ci
        self.mcad_test = mcad_test

        self.generate_plots_from_pr_args = generate_plots_from_pr_args
        self.generate_plots = generate_plots

        self.mcad_run_one_matbench = mcad_run_one_matbench
        self.sdk_user_run_one = sdk_user_run_one


def main():
    # Print help rather than opening a pager
    fire.core.Display = lambda lines, out: print(*lines, file=out)

    fire.Fire(Entrypoint())


if __name__ == "__main__":
    try:
        sys.exit(main())
    except subprocess.CalledProcessError as e:
        logging.error(f"Command '{e.cmd}' failed --> {e.returncode}")
        sys.exit(1)
    except KeyboardInterrupt:
        print() # empty line after ^C
        logging.error(f"Interrupted.")
        sys.exit(1)
