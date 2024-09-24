#!/usr/bin/env python

import sys, os
import pathlib
import subprocess
import logging
logging.getLogger().setLevel(logging.INFO)
import datetime
import time
import functools

import yaml
import fire

from projects.core.library import env, config, run, rhods
from projects.matrix_benchmarking.library import visualize

PIPELINES_OPERATOR_MANIFEST_NAME = "openshift-pipelines-operator-rh"

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
def prepare_ci():
    """
    Prepares the cluster and the namespace for running Load-Aware scale tests
    """

    test_namespace = config.ci_artifacts.get_config("load_aware.scale_test.namespace")
    run.run(f"oc create ns {test_namespace}")

    run.run_toolbox_from_config("cluster", "set_scale", prefix="sutest")
    run.run_toolbox_from_config("cluster", "set_project_annotation", prefix="sutest", suffix="node_selector")
    run.run_toolbox_from_config("cluster", "set_project_annotation", prefix="sutest", suffix="toleration")

    install_ocp_pipelines()

    run.run_toolbox_from_config("cluster", "capture_environment", suffix="sample")
    run.run_toolbox_from_config("load_aware", "deploy_trimaran")

    run.run_toolbox("cluster deploy_kepler")

    run.run_toolbox_from_config("cluster", "build_push_image", suffix="deps")
    run.run_toolbox_from_config("cluster", "build_push_image", suffix="make")
    run.run_toolbox_from_config("cluster", "preload_image", suffix="deps")
    run.run_toolbox_from_config("cluster", "preload_image", suffix="make")
    run.run_toolbox_from_config("cluster", "preload_image",  suffix="sleep") # preloads ubi8

def _run_test(test_artifact_dir_p, scheduler_name):
    """
    Runs the Load-Aware scale test from the CI
    """

    next_count = env.next_artifact_index()
    with env.TempArtifactDir(env.ARTIFACT_DIR / f"{next_count:03d}__load_aware_scale_test_{scheduler_name}_scheduler"):
        test_artifact_dir_p[0] = env.ARTIFACT_DIR

        with open(env.ARTIFACT_DIR / "settings", "w") as f:
            print(f"scheduler={scheduler_name}", file=f)

        with open(env.ARTIFACT_DIR / "config.yaml", "w") as f:
            yaml.dump(config.ci_artifacts.config, f, indent=4)

        # clean up pods from previous test
        test_namespace = config.ci_artifacts.get_config("load_aware.scale_test.namespace")
        run.run(f"oc delete pods --all -n {test_namespace} --ignore-not-found")
        run.run_toolbox("cluster reset_prometheus_db")

        failed = True
        try:
            extra = {}
            extra["scheduler"] = scheduler_name
            run.run_toolbox_from_config("load_aware", "scale_test", extra=extra)

            failed = False
        finally:
            with open(env.ARTIFACT_DIR / "exit_code", "w") as f:
                print("1" if failed else "0", file=f)

            run.run_toolbox_from_config("cluster", "capture_environment", suffix="sample")
            run.run_toolbox("cluster", "dump_prometheus_db")


@entrypoint()
def test_ci():
    """
    Runs the Load-Aware scale test from the CI
    """

    try:
        for scheduler_name in config.ci_artifacts.get_config("load_aware.schedulers"):
            try:
                test_artifact_dir_p = [None]
                _run_test(test_artifact_dir_p, scheduler_name)
            finally:
                if test_artifact_dir_p[0] is not None:
                    next_count = env.next_artifact_index()
                    with env.TempArtifactDir(env.ARTIFACT_DIR / f"{next_count:03d}__{scheduler_name}_plots"):
                        generate_plots(test_artifact_dir_p[0])
                else:
                    logging.warning("Not generating the visualization as the test artifact directory hasn't been created.")
    finally:
        results_dir = env.ARTIFACT_DIR
        matbench_config_file = config.ci_artifacts.get_config("load_aware.matbench_comparison_file")
        next_count = env.next_artifact_index()
        with (env.TempArtifactDir(env.ARTIFACT_DIR / f"{next_count:03d}__comparison_plots"),
              config.TempValue(config.ci_artifacts, "matbench.config_file", matbench_config_file)):
            visualize.generate_from_dir(results_dir)

        run.run(f"testing/utils/generate_plot_index.py > {env.ARTIFACT_DIR}/reports_index.html", check=False)

        if config.ci_artifacts.get_config("clusters.cleanup_on_exit"):
            cleanup_cluster()

@entrypoint(ignore_secret_path=True, apply_preset_from_pr_args=False)
def generate_plots_from_pr_args():
    """
    Generates the Load-Aware plots from the PR arguments
    """

    visualize.download_and_generate_visualizations()


@entrypoint()
def cleanup_cluster():
    """
    Restores the cluster to its original state
    """
    # _Not_ executed in OpenShift CI cluster (running on AWS). Only required for running on bare-metal environments.
    logging.info("Cleaning up cluster and uninstall pipelines")
    test_namespace = config.ci_artifacts.get_config("load_aware.scale_test.namespace")
    run.run("oc delete ns {test_namespace} --ignore-not-found")
    run.run_toolbox("load_aware undeploy_trimaran")
    run.run_toolbox("cluster undeploy_kepler")

    uninstall_ocp_pipelines()


@entrypoint(ignore_secret_path=True)
def generate_plots(results_dirname):
    visualize.generate_from_dir(str(results_dirname))


def install_ocp_pipelines():
    installed_csv_cmd = run.run("oc get csv -oname", capture_stdout=True)
    if PIPELINES_OPERATOR_MANIFEST_NAME in installed_csv_cmd.stdout:
        logging.info(f"Operator '{PIPELINES_OPERATOR_MANIFEST_NAME}' is already installed.")
        return

    run.run_toolbox("cluster", "deploy_operator", catalog="redhat-operators", manifest_name=PIPELINES_OPERATOR_MANIFEST_NAME, all=True, artifact_dir_suffix="_pipelines")

def uninstall_ocp_pipelines():
    installed_csv_cmd = run.run("oc get csv -oname", capture_stdout=True)
    if PIPELINES_OPERATOR_MANIFEST_NAME not in installed_csv_cmd.stdout:
        logging.info("Pipelines Operator is not installed")
        return

    run.run(f"oc delete tektonconfigs.operator.tekton.dev --all")
    PIPELINES_OPERATOR_NAMESPACE = "openshift-operators"
    run.run(f"oc delete sub/{PIPELINES_OPERATOR_MANIFEST_NAME} -n {PIPELINES_OPERATOR_NAMESPACE}")
    run.run(f"oc delete csv -n {PIPELINES_OPERATOR_NAMESPACE} -loperators.coreos.com/{PIPELINES_OPERATOR_MANIFEST_NAME}.{PIPELINES_OPERATOR_NAMESPACE}")

# ---

class Entrypoint:
    """
    Commands for launching the Load-Aware CI tests
    """

    def __init__(self):
        self.cleanup_cluster_ci = cleanup_cluster

        self.prepare_ci = prepare_ci
        self.test_ci = test_ci

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
