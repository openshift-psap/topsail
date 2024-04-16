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

    logging.info("Nothing to do to prepare the cluster.")

    run.run_toolbox_from_config("cluster", "capture_environment", suffix="sample")



def _run_test(test_artifact_dir_p):
    next_count = env.next_artifact_index()
    with env.TempArtifactDir(env.ARTIFACT_DIR / f"{next_count:03d}__dummy_test"):
        test_artifact_dir_p[0] = env.ARTIFACT_DIR

        with open(env.ARTIFACT_DIR / "settings.yaml", "w") as f:
            yaml.dump(dict(dummy=True), f, indent=4)

        with open(env.ARTIFACT_DIR / "config.yaml", "w") as f:
            yaml.dump(config.ci_artifacts.config, f, indent=4)

        with open(env.ARTIFACT_DIR / ".uuid", "w") as f:
            print(str(uuid.uuid4()), file=f)

        sleep_duration = config.ci_artifacts.get_config("tests.sleep_duration")
        capture_prometheus = config.ci_artifacts.get_config("tests.capture_prometheus")
        failed = True
        try:
            if capture_prometheus:
                run.run_toolbox("cluster", "reset_prometheus_db")

            logging.info(f"Waiting {sleep_duration} minutes to capture some metrics in Prometheus ...")
            time.sleep(sleep_duration * 60)

            if capture_prometheus:
                run.run_toolbox("cluster", "dump_prometheus_db")
            failed = False
        finally:
            with open(env.ARTIFACT_DIR / "exit_code", "w") as f:
                print("1" if failed else "0", file=f)

            run.run_toolbox_from_config("cluster", "capture_environment", suffix="sample")


@entrypoint()
def test_ci():
    """
    Runs the test from the CI
    """

    try:
        test_artifact_dir_p = [None]
        _run_test(test_artifact_dir_p)
    finally:
        try:
            if test_artifact_dir_p[0] is not None:
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
def cleanup_cluster():
    """
    Restores the cluster to its original state
    """
    # _Not_ executed in OpenShift CI cluster (running on AWS). Only required for running in bare-metal environments.

    logging.info("Nothing to do to cleanup the cluster.")


@entrypoint(ignore_secret_path=True)
def generate_plots(results_dirname):
    visualize.generate_from_dir(str(results_dirname))


@entrypoint(ignore_secret_path=True)
def export_artifacts(artifacts_dirname):
    export.export_artifacts(artifacts_dirname)

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
