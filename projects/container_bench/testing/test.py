#!/usr/bin/env python

import sys
import subprocess
import logging
import prepare
import test_container_bench
import fire

from entrypoint import entrypoint
from projects.core.library import env, export
from projects.matrix_benchmarking.library import visualize

logging.getLogger().setLevel(logging.INFO)


# ---


@entrypoint()
def prepare_ci():
    """
    Prepares the cluster and the namespace for running the tests
    """

    return prepare.prepare()


@entrypoint()
def test_ci():
    """
    Runs the test from the CI
    """

    try:
        failed = test_container_bench.test()
        logging.info("container_bench.test " + ("failed" if failed else "passed"))

        return 1 if failed else 0
    finally:
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

    return prepare.cleanup()


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

    test_container_bench.matbench_run_one()

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
        print()  # empty line after ^C
        logging.error("Interrupted.")
        sys.exit(1)
