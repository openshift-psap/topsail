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

from projects.core.library import env, config, run, visualize, export
import prepare_finetuning, test_finetuning

TESTING_THIS_DIR = pathlib.Path(__file__).absolute().parent

PSAP_ODS_SECRET_PATH = pathlib.Path(os.environ.get("PSAP_ODS_SECRET_PATH", "/env/PSAP_ODS_SECRET_PATH/not_set"))
LIGHT_PROFILE = "light"
METAL_PROFILE = "metal"

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
        if not PSAP_ODS_SECRET_PATH.exists():
            raise RuntimeError(f"Path with the secrets (PSAP_ODS_SECRET_PATH={PSAP_ODS_SECRET_PATH}) does not exists.")

        run.run(f'sha256sum "$PSAP_ODS_SECRET_PATH"/* > "{env.ARTIFACT_DIR}/secrets.sha256sum"')

    config.ci_artifacts.detect_apply_light_profile(LIGHT_PROFILE)
    is_metal = config.ci_artifacts.detect_apply_metal_profile(METAL_PROFILE)

    if is_metal:
        metal_profiles = config.ci_artifacts.get_config("clusters.metal_profiles")
        profile_applied = config.ci_artifacts.detect_apply_cluster_profile(metal_profiles)

        if not profile_applied:
            raise ValueError("Bare-metal cluster not recognized :/ ")

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

    prepare_finetuning.prepare()


@entrypoint()
def test_ci():
    """
    Runs the test from the CI
    """

    try:
        test_artifact_dir_p = [None]
        test_artifact_dir_p[0] = env.ARTIFACT_DIR
        test_finetuning.test()
    finally:
        try:
            if not config.ci_artifacts.get_config("tests.fine_tuning.matbenchmarking.enabled"):
                logging.warning("Not generating the visualization as it was already generated and it wasn't a MatBenchmarking run.")
            elif not config.ci_artifacts.get_config("tests.visualize"):
                logging.warning("Not generating the visualization as it is disabled in the configuration.")
            elif test_artifact_dir_p[0] is not None:
                next_count = env.next_artifact_index()
                with env.TempArtifactDir(env.ARTIFACT_DIR / f"{next_count:03d}__plots"):
                    visualize.prepare_matbench()
                    generate_plots(test_artifact_dir_p[0])
            else:
                logging.warning("Not generating the visualization as the test artifact directory hasn't been created.")

        finally:
            run.run(f"testing/utils/generate_plot_index.py > {env.ARTIFACT_DIR}/reports_index.html", check=False)

            if config.ci_artifacts.get_config("clusters.cleanup_on_exit"):
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
def cleanup_cluster(mute=False):
    """
    Restores the cluster to its original state
    """
    # _Not_ executed in OpenShift CI cluster (running on AWS). Only required for running in bare-metal environments.

    prepare_finetuning.cleanup_cluster()


@entrypoint(ignore_secret_path=True)
def generate_plots(results_dirname):
    visualize.generate_from_dir(str(results_dirname))


@entrypoint(ignore_secret_path=True)
def export_artifacts(artifacts_dirname):
    export.export_artifacts(artifacts_dirname)

@entrypoint(ignore_secret_path=True)
def prepare_namespace():
    """
    Prepares the namespace where the fine-tuning jobs will be executed
    """

    return prepare_finetuning.prepare_namespace()


@entrypoint()
def matbench_run_one():
    """
    Runs one test as part of a MatrixBenchmark benchmark
    """

    test_finetuning.matbench_run_one()

# ---

class Entrypoint:
    """
    Commands for launching the CI tests
    """

    def __init__(self):
        self.cleanup_cluster_ci = cleanup_cluster

        self.prepare_ci = prepare_ci
        self.test_ci = test_ci
        self.export_artifacts = export_artifacts

        self.generate_plots_from_pr_args = generate_plots_from_pr_args
        self.generate_plots = generate_plots
        self.prepare_namespace = prepare_namespace

        self.matbench_run_one = matbench_run_one
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
