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

from projects.core.library import env, config, run, configure_logging, export
configure_logging()
from projects.matrix_benchmarking.library import visualize
import prepare, test_schedulers


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

    config.project.detect_apply_light_profile(LIGHT_PROFILE)
    is_metal = config.project.detect_apply_metal_profile(METAL_PROFILE)

    if is_metal:
        metal_profiles = config.project.get_config("clusters.metal_profiles")
        profile_applied = config.project.detect_apply_cluster_profile(metal_profiles)

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

    test_mode = config.project.get_config("tests.mode")
    prepare.prepare()


@entrypoint()
def test_ci():
    """
    Runs the test from the CI
    """

    do_visualize = config.project.get_config("tests.visualize")

    try:
        test_artifact_dir_p = [None]
        test_artifact_dir_p[0] = env.ARTIFACT_DIR
        test_schedulers.test()
    finally:
        matbenchmarking = config.project.get_config("tests.fine_tuning.matbenchmarking.enabled")

        if horreum_test := config.project.get_config("matbench.lts.horreum.test_name"):
            logging.info(f"Saving Horreum test name: {horreum_test}")
            with open(env.ARTIFACT_DIR / "test_name.horreum", "w") as f:
                print(horreum_test, file=f)
        else:
            logging.info(f"No Horreum test name to save")

        if config.project.get_config("clusters.cleanup_on_exit"):
            cleanup_cluster(mute=True)

        export.export_artifacts(env.ARTIFACT_DIR, "test_ci")


@entrypoint(ignore_secret_path=True, apply_preset_from_pr_args=False)
def generate_plots_from_pr_args():
    """
    Generates the visualization reports from the PR arguments
    """

    try:
        os.environ["AWS_SHARED_CREDENTIALS_FILE"] = str(pathlib.Path(os.environ["PSAP_ODS_SECRET_PATH"]) / config.project.get_config("secrets.aws_credentials"))
    except Exception as e:
        logging.warning(f"Failed to set AWS_SHARED_CREDENTIALS_FILE: {e}")

    visualize.download_and_generate_visualizations()

    export.export_artifacts(env.ARTIFACT_DIR, test_step="plot")


@entrypoint()
def cleanup_cluster(mute=False):
    """
    Restores the cluster to its original state
    """
    # _Not_ executed in OpenShift CI cluster (running on AWS). Only required for running in bare-metal environments.

    with env.NextArtifactDir("cleanup_cluster"):
        cleanup_sutest_ns()
        cluster_scale_down()

        prepare.cleanup_rhoai(mute)


@entrypoint()
def cleanup_rhoai(mute=False):
    """
    Restores the cluster to its original state
    """
    prepare.cleanup_rhoai(mute)


@entrypoint(ignore_secret_path=True)
def generate_plots(results_dirname):

    visualize.generate_from_dir(str(results_dirname))
    logging.info(f"Plots have been generated in {env.ARTIFACT_DIR}")


@entrypoint()
def cluster_scale_up():
    """
    Scales up the cluster SUTest and Driver machinesets
    """
    return prepare.cluster_scale_up()


@entrypoint()
def cluster_scale_down(to_zero=False):
    """
    Scales down the cluster SUTest and Driver machinesets
    """
    return prepare.cluster_scale_down(to_zero)


@entrypoint()
def cleanup_sutest_ns():
    """
    Cleans up the SUTest namespaces
    """

    prepare.cleanup_sutest_ns()


@entrypoint(ignore_secret_path=True)
def export_artifacts(artifacts_dirname):
    export.export_artifacts(artifacts_dirname)


@entrypoint()
def matbench_run_one():
    """
    Runs one test as part of a MatrixBenchmark benchmark
    """

    test_schedulers.matbench_run_one()


@entrypoint(ignore_secret_path=True)
def run_kwok_job_controller():
    """
    Runs KWOK Job Controller
    """

    controller_path = TESTING_THIS_DIR / "kwok-job-controller" / "controller.py"
    if not controller_path.exists():
        raise FileNotFoundError(f"Controller file not found: {controller_path}")

    namespace = config.project.get_config("tests.schedulers.namespace")

    run.run(f"kopf run {controller_path} -n {namespace}")

    raise ValueError("kopf controller should not return ...")

# ---

class Entrypoint:
    """
    Commands for launching the CI tests
    """

    def __init__(self):
        self.cleanup_cluster_ci = cleanup_cluster
        self.cleanup_cluster = cleanup_cluster

        self.prepare_ci = prepare_ci
        self.cluster_scale_up = cluster_scale_up
        self.cluster_scale_down = cluster_scale_down

        self.test_ci = test_ci
        self.generate_plots_from_pr_args = generate_plots_from_pr_args

        self.export_artifacts = export_artifacts

        self.cleanup_sutest_ns = cleanup_sutest_ns

        self.matbench_run_one = matbench_run_one

        self.run_kwok_job_controller = run_kwok_job_controller

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
