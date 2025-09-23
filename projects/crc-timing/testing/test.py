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

import prepare_crc_timing, test_crc_timing

from entrypoint import entrypoint

# ---

@entrypoint()
def prepare_ci():
    """
    Prepares the cluster and the namespace for running the tests
    """
    try:
        return prepare_crc_timing.prepare()
    finally:
        if not config.project.get_config("remote_host.run_locally"):
            # retrieve all the files that have been saved remotely
            exc = None
            exc = run.run_and_catch(exc, run.run_toolbox, "remote", "retrieve",
                                    path=env.ARTIFACT_DIR, dest=env.ARTIFACT_DIR,
                                    mute_stdout=True, mute_stderr=True)
            if exc:
                logging.error(f"Remote retrieve failed :/ --> {exc}")


@entrypoint()
def test_ci():
    """
    Runs the test from the CI
    """

    try:
        try:
            failed = test_crc_timing.test()
            logging.info("test_crc_timing.test " + ("failed" if failed else "passed"))
        finally:
            if not config.project.get_config("remote_host.run_locally"):
                # retrieve all the files that have been saved remotely
                exc = None
                exc = run.run_and_catch(exc, run.run_toolbox, "remote", "retrieve",
                                        path=env.ARTIFACT_DIR, dest=env.ARTIFACT_DIR,
                                        mute_stdout=True, mute_stderr=True)
                if exc:
                    logging.error(f"Remote retrieve failed :/ --> {exc}")
                    failed = True

            if config.project.get_config("matbench.enabled"):
                exc = generate_visualization(env.ARTIFACT_DIR)
                if exc:
                    logging.error(f"Test visualization failed :/ {exc}")
                    failed = True
                else:
                    logging.info(f"Test artifacts have been saved in {env.ARTIFACT_DIR}")

        return 1 if failed else 0
    finally:
        if config.project.get_config("cleanup.cleanup_on_exit"):
            prepare_crc_timing.cleanup()


def generate_visualization(test_artifact_dir):
    exc = None

    with env.NextArtifactDir("plots"):
        exc = run.run_and_catch(exc, visualize.generate_from_dir, test_artifact_dir)

        logging.info(f"Test visualization has been generated into {env.ARTIFACT_DIR}/reports_index.html")

    return exc



@entrypoint(ignore_secret_path=True, apply_preset_from_pr_args=False)
def generate_plots_from_pr_args():
    """
    Generates the visualization reports from the PR arguments
    """

    visualize.download_and_generate_visualizations()


@entrypoint()
def cleanup_ci(mute=False):
    """
    Restores the cluster to its original state
    """
    # _Not_ executed in OpenShift CI cluster (running on AWS). Only required for running in bare-metal environments.

    return prepare_crc_timing.cleanup()


@entrypoint(ignore_secret_path=True)
def generate_plots(results_dirname):
    visualize.generate_from_dir(str(results_dirname))

# ---

class Entrypoint:
    """
    Commands for launching the CI tests
    """

    def __init__(self):
        self.pre_cleanup_ci = cleanup_ci
        self.post_cleanup_ci = cleanup_ci
        self.prepare_ci = prepare_ci
        self.test_ci = test_ci

        self.generate_plots_from_pr_args = generate_plots_from_pr_args
        self.generate_plots = generate_plots

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
