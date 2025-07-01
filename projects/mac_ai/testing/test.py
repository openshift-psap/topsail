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

from entrypoint import entrypoint

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

    return prepare_mac_ai.cleanup()


@entrypoint(ignore_secret_path=True)
def generate_plots(results_dirname):
    visualize.generate_from_dir(str(results_dirname))


@entrypoint(ignore_secret_path=True)
def export_artifacts(artifacts_dirname):
    export.export_artifacts(artifacts_dirname)


@entrypoint(apply_preset_from_pr_args=False)
def matbench_run():
    """
    Runs one test as part of a MatrixBenchmark benchmark, includuing the deployment phase
    """

    test_mac_ai.matbench_run_one()

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

        self.export_artifacts = export_artifacts

        self.generate_plots_from_pr_args = generate_plots_from_pr_args
        self.generate_plots = generate_plots

        self.matbench_run = matbench_run

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
