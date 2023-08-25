#!/usr/bin/env python

import sys, os
import pathlib
import subprocess
import logging
import datetime
import time
import functools

import yaml
import fire

TESTING_THIS_DIR = pathlib.Path(__file__).absolute().parent
TESTING_UTILS_DIR = TESTING_THIS_DIR.parent / "utils"
PSAP_ODS_SECRET_PATH = pathlib.Path(os.environ.get("PSAP_ODS_SECRET_PATH", "/env/PSAP_ODS_SECRET_PATH/not_set"))
LIGHT_PROFILE = "light"

sys.path.append(str(TESTING_THIS_DIR.parent))
from common import env, config, run, rhods, visualize, configure_logging
configure_logging()

import prepare_scale, test_scale
import prepare_watsonx_serving

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
        raise RuntimeError(f"Path with the secrets (PSAP_ODS_SECRET_PATH={PSAP_ODS_SECRET_PATH}) does not exists.")


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
def prepare_ci():
    """
    Prepares the cluster and the namespace for running the tests
    """

    test_mode = config.ci_artifacts.get_config("tests.mode")
    if test_mode == "scale":
        prepare_scale.prepare()
    else:
        raise KeyError(f"Invalid test mode: {test_mode}")


@entrypoint()
def test_ci():
    """
    Runs the test from the CI
    """

    do_visualize = config.ci_artifacts.get_config("tests.visualize")

    try:
        test_artifact_dir_p = [None]
        _run_test(test_artifact_dir_p=test_artifact_dir_p)
    finally:
        try:
            if not do_visualize:
                logging.info("Not generating the visualization because it isn't activated.")
            elif test_artifact_dir_p[0] is not None:
                next_count = env.next_artifact_index()
                with env.TempArtifactDir(env.ARTIFACT_DIR / f"{next_count:03d}__plots"):
                    visualize.prepare_matbench()
                    generate_plots(test_artifact_dir_p[0])
            else:
                logging.warning("Not generating the visualization as the test artifact directory hasn't been created.")

        finally:
            if do_visualize:
                run.run(f"testing/utils/generate_plot_index.py > {env.ARTIFACT_DIR}/report_index.html", check=False)

            if config.ci_artifacts.get_config("clusters.cleanup_on_exit"):
                cleanup_cluster()

@entrypoint()
def scale_test(dry_mode=None, capture_prom=None, do_visualize=None):
    """
    Runs the test from the CI

    Args:
      do_visualize: if False, do not generate the visualization reports
      dry_mode: if True, do not execute the tests, only list what would be executed
      capture_prom: if False, do not capture Prometheus database
    """

    if dry_mode is not None:
        config.ci_artifacts.set_config("tests.dry_mode", dry_mode)

    if capture_prom is not None:
        config.ci_artifacts.set_config("tests.capture_prom", capture_prom)

    if do_visualize is not None:
        config.ci_artifacts.set_config("tests.visualize", do_visualize)

    test_scale.test()


@entrypoint()
def run_one(dry_mode=None, capture_prom=None, do_visualize=None):
    """
    Runs the test with single user

    Args:
      do_visualize: if False, do not generate the visualization reports
      dry_mode: if True, do not execute the tests, only list what would be executed
      capture_prom: if False, do not capture Prometheus database
    """

    test_mode = config.ci_artifacts.get_config("tests.mode")

    if test_mode != "scale":
        raise KeyError(f"Invalid test mode: {test_mode}")

    if dry_mode is not None:
        config.ci_artifacts.set_config("tests.dry_mode", dry_mode)

    if capture_prom is not None:
        config.ci_artifacts.set_config("tests.capture_prom", capture_prom)

    if do_visualize is not None:
        config.ci_artifacts.set_config("tests.visualize", do_visualize)

    test_scale.run_one()


def _run_test(test_artifact_dir_p):
    test_mode = config.ci_artifacts.get_config("tests.mode")
    if test_mode == "scale":
        test_scale.test(test_artifact_dir_p)
    else:
        raise KeyError(f"Invalid test mode: {test_mode}")


@entrypoint(ignore_secret_path=True, apply_preset_from_pr_args=False)
def generate_plots_from_pr_args():
    """
    Generates the visualization reports from the PR arguments
    """

    visualize.download_and_generate_visualizations()


@entrypoint()
def cleanup_cluster():
    """
    Restores the cluster to its original state
    """
    # _Not_ executed in OpenShift CI cluster (running on AWS). Only required for running in bare-metal environments.

    logging.info("Nothing to do to cleanup the cluster.")


@entrypoint(ignore_secret_path=True)
def generate_plots(results_dirname):
    visualize.generate_from_dir(str(results_dirname))


@entrypoint()
def _prepare_watsonx_serving():
    return prepare_watsonx_serving.prepare()

# ---

class Entrypoint:
    """
    Commands for launching the CI tests
    """

    def __init__(self):
        self.cleanup_cluster_ci = cleanup_cluster

        self.prepare_ci = prepare_ci
        self.prepare_watsonx_serving = _prepare_watsonx_serving

        self.test_ci = test_ci
        self.scale_test = scale_test
        self.run_one = run_one
        self.generate_plots_from_pr_args = generate_plots_from_pr_args
        self.generate_plots = generate_plots

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
