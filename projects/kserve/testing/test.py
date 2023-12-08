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

from topsail.testing import env, config, run, rhods, visualize, configure_logging, prepare_user_pods
configure_logging()

import prepare_scale, test_scale, test_e2e
import prepare_kserve

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
    config.init(TESTING_THIS_DIR)

    if apply_preset_from_pr_args:
        config.ci_artifacts.apply_preset_from_pr_args()

    if not ignore_secret_path and not PSAP_ODS_SECRET_PATH.exists():
        raise RuntimeError(f"Path with the secrets (PSAP_ODS_SECRET_PATH={PSAP_ODS_SECRET_PATH}) does not exists.")

    config.ci_artifacts.detect_apply_light_profile(LIGHT_PROFILE)
    config.ci_artifacts.detect_apply_metal_profile(METAL_PROFILE)


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
    if test_mode in ("scale", "e2e"):
        prepare_scale.prepare()
    else:
        raise KeyError(f"Invalid test mode: {test_mode}")


@entrypoint()
def test_ci():
    """
    Runs the test from the CI
    """

    test_mode = config.ci_artifacts.get_config("tests.mode")

    do_visualize = config.ci_artifacts.get_config("tests.visualize")

    try:
        test_artifact_dir_p = [None]
        if test_mode == "e2e":
            test_artifact_dir_p[0] = env.ARTIFACT_DIR
            test_e2e.test_ci()
        else:
            assert test_mode == "scale"
            _run_test(test_artifact_dir_p=test_artifact_dir_p)
    finally:
        try:
            if not do_visualize:
                logging.info("Not generating the visualization because it isn't activated.")
            elif test_artifact_dir_p[0] is not None:
                with env.NextArtifactDir("plots"):
                    visualize.prepare_matbench()
                    generate_plots(test_artifact_dir_p[0])
            else:
                logging.warning("Not generating the visualization as the test artifact directory hasn't been created.")

        finally:
            if do_visualize:
                run.run(f"testing/utils/generate_plot_index.py > {env.ARTIFACT_DIR}/report_index.html", check=False)

            if config.ci_artifacts.get_config("clusters.cleanup_on_exit"):
                cleanup_cluster(mute=True)

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
def cleanup_cluster(mute=False):
    """
    Restores the cluster to its original state
    """
    # _Not_ executed in OpenShift CI cluster (running on AWS). Only required for running in bare-metal environments.

    with env.NextArtifactDir("cleanup_cluster"):
        cleanup_sutest_ns()
        cluster_scale_down()
        prepare_user_pods.cleanup_cluster()
        cleanup_sutest_crs()

    prepare_kserve.cleanup(mute)


@entrypoint()
def cleanup_rhoai(mute=False):
    """
    Restores the cluster to its original state
    """
    prepare_kserve.cleanup(mute)


@entrypoint(ignore_secret_path=True)
def generate_plots(results_dirname):
    try:
        main_workload = config.ci_artifacts.get_config("matbench.workload")
        with env.NextArtifactDir(f"{main_workload}_plots"):
            visualize.generate_from_dir(str(results_dirname))
    finally:
        exc = None
        prom_workload = config.ci_artifacts.get_config("tests.prom_plot_workload")
        if not prom_workload:
            logging.info(f"Setting tests.prom_plot_workload isn't set, nothing else to generate.")
            return

        with config.TempValue(config.ci_artifacts, "matbench.workload", prom_workload):
            visualize.prepare_matbench()

            with env.NextArtifactDir(f"{prom_workload}__all"):
                logging.info(f"Generating the plots with workload={prom_workload}")
                try:
                    visualize.generate_from_dir(str(results_dirname))
                except Exception as e:
                    exc = e
                    logging.error(f"Generating the plots with workload={prom_workload} --> FAILED")

            for prom_dir in pathlib.Path(results_dirname).glob("**/.matbench_prom_db_dir"):
                current_results_dirname = prom_dir.parent
                if current_results_dirname == results_dirname: continue
                dirname = current_results_dirname.name

                with env.NextArtifactDir(f"{prom_workload}__{dirname}"):
                    logging.info(f"Generating the plots with workload={prom_workload} for {current_results_dirname}")
                    try:
                        visualize.generate_from_dir(str(current_results_dirname), generate_lts=False)
                    except Exception as e:
                        exc = e
                        logging.error(f"Generating the plots with workload={prom_workload} for {current_results_dirname} --> FAILED")
        if exc is not None:
            raise exc

    logging.info(f"Plots have been generated in {env.ARTIFACT_DIR}")


@entrypoint()
def _prepare_kserve():
    """
    Installs RHOAI KServe stack on the cluster
    """
    return prepare_kserve.prepare()


@entrypoint()
def cluster_scale_up():
    """
    Scales up the cluster SUTest and Driver machinesets
    """
    return prepare_scale.cluster_scale_up()


@entrypoint()
def cluster_scale_down(to_zero=False):
    """
    Scales down the cluster SUTest and Driver machinesets
    """
    return prepare_scale.cluster_scale_down(to_zero)


@entrypoint()
def cleanup_sutest_ns():
    """
    Cleans up the SUTest namespaces
    """

    label = config.ci_artifacts.get_config("tests.scale.namespace.label")
    run.run(f"oc delete ns -l{label}")


@entrypoint()
def cleanup_sutest_crs():
    """
    Cleans up the Custom Resources of the SUTest cluster
    """

    run.run_toolbox("rhods", "update_datasciencecluster", enable=["kserve"])
    for cr_name in config.ci_artifacts.get_config("prepare.cleanup.crds"):
        run.run(f"oc delete {cr_name} --all -A")


@entrypoint()
def rebuild_driver_image(pr_number):
    namespace = config.ci_artifacts.get_config("base_image.namespace")
    prepare_user_pods.rebuild_driver_image(namespace, pr_number)

# ---

class Entrypoint:
    """
    Commands for launching the CI tests
    """

    def __init__(self):
        self.cleanup_cluster_ci = cleanup_cluster
        self.cleanup_cluster = cleanup_cluster
        self.cleanup_rhoai = cleanup_rhoai

        self.prepare_ci = prepare_ci
        self.prepare_kserve = _prepare_kserve
        self.cluster_scale_up = cluster_scale_up
        self.cluster_scale_down = cluster_scale_down
        self.rebuild_driver_image = rebuild_driver_image

        self.test_ci = test_ci
        self.scale_test = scale_test
        self.run_one = run_one
        self.generate_plots_from_pr_args = generate_plots_from_pr_args
        self.generate_plots = generate_plots

        self.cleanup_sutest_ns = cleanup_sutest_ns

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
