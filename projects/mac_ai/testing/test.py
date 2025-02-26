#!/usr/bin/env python

import sys, os
import pathlib
import subprocess
import logging
logging.getLogger().setLevel(logging.INFO)
import datetime
import time
import functools
import uuid

import yaml
import fire

from projects.core.library import env, config, run, export, common
from projects.matrix_benchmarking.library import visualize

import prepare_mac_ai, test_mac_ai

TESTING_THIS_DIR = pathlib.Path(__file__).absolute().parent

CRC_MAC_AI_SECRET_PATH = pathlib.Path(os.environ.get("CRC_MAC_AI_SECRET_PATH", "/env/CRC_MAC_AI_SECRET_PATH/not_set"))

initialized = False
def init(ignore_secret_path=False, apply_preset_from_pr_args=True):
    global initialized
    if initialized:
        logging.debug("Already initialized.")
        return
    initialized = True

    env.init()
    config.init(TESTING_THIS_DIR, apply_preset_from_pr_args)

    if not ignore_secret_path:
        if not CRC_MAC_AI_SECRET_PATH.exists():
            raise RuntimeError(f"Path with the secrets (CRC_MAC_AI_SECRET_PATH={CRC_MAC_AI_SECRET_PATH}) does not exists.")

        run.run(f'sha256sum "$CRC_MAC_AI_SECRET_PATH"/* > "{env.ARTIFACT_DIR}/secrets.sha256sum"')


def entrypoint(ignore_secret_path=False, apply_preset_from_pr_args=True):
    def decorator(fct):
        @functools.wraps(fct)
        def wrapper(*args, **kwargs):
            init(ignore_secret_path, apply_preset_from_pr_args)
            exit_code = fct(*args, **kwargs)
            logging.info(f"exit code of {fct.__qualname__}: {exit_code}")
            if exit_code is None:
                exit_code = 0
            raise SystemExit(exit_code)

        return wrapper
    return decorator

# ---

@entrypoint()
def prepare_ci():
    """
    Prepares the cluster and the namespace for running the tests
    """

    return prepare_mac_ai.prepare()


@entrypoint()
def test_ci():
    """
    Runs the test from the CI
    """

    try:
        test_artifact_dir_p = [None]
        test_artifact_dir_p[0] = env.ARTIFACT_DIR

        failed = test_mac_ai.test()
        logging.info("test_mac_ai.test " + ("failed" if failed else "passed"))

        return 1 if failed else 0
    finally:
        if config.project.get_config("prepare.cleanup_on_exit"):
            cleanup_cluster()

        export.export_artifacts(env.ARTIFACT_DIR, test_step="test_ci")


@entrypoint(ignore_secret_path=True, apply_preset_from_pr_args=False)
def generate_plots_from_pr_args():
    """
    Generates the visualization reports from the PR arguments
    """

    visualize.download_and_generate_visualizations()

    export.export_artifacts(env.ARTIFACT_DIR, test_step="plot")


@entrypoint()
def cleanup_ci(mute=False):
    """
    Restores the cluster to its original state
    """
    # _Not_ executed in OpenShift CI cluster (running on AWS). Only required for running in bare-metal environments.

    prepare_mac_ai.cleanup()


@entrypoint(ignore_secret_path=True)
def generate_plots(results_dirname):
    visualize.generate_from_dir(str(results_dirname))


@entrypoint(ignore_secret_path=True)
def export_artifacts(artifacts_dirname):
    export.export_artifacts(artifacts_dirname)


@entrypoint()
def matbench_run_with_deploy():
    """
    Runs one test as part of a MatrixBenchmark benchmark, includuing the deployment phase
    """

    test_mac_ai.matbench_run_one(with_deploy=True)


@entrypoint()
def matbench_run_without_deploy():
    """
    Runs one test as part of a MatrixBenchmark benchmark, excluding the deployment phase (llm-load-test only)
    """

    test_mac_ai.matbench_run_one(with_deploy=False)

# ---

class Entrypoint:
    """
    Commands for launching the CI tests
    """

    def __init__(self):
        self.pre_cleanup_ci = cleanup_ci
        self.prepare_ci = prepare_ci
        self.test_ci = test_ci

        self.export_artifacts = export_artifacts

        self.generate_plots_from_pr_args = generate_plots_from_pr_args
        self.generate_plots = generate_plots

        self.matbench_run_with_deploy = matbench_run_with_deploy
        self.matbench_run_without_deploy = matbench_run_without_deploy

# ---

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
