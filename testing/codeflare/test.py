#!/usr/bin/env python3

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

TESTING_THIS_DIR = pathlib.Path(__file__).absolute().parent
TESTING_UTILS_DIR = TESTING_THIS_DIR.parent / "utils"
PSAP_ODS_SECRET_PATH = pathlib.Path(os.environ.get("PSAP_ODS_SECRET_PATH", "/env/PSAP_ODS_SECRET_PATH/not_set"))
LIGHT_PROFILE = "light"

sys.path.append(str(TESTING_THIS_DIR.parent))
from common import env, config, run, rhods, visualize


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

def prepare_mcad_test():
    namespace = config.ci_artifacts.get_config("tests.mcad.namespace")
    if run.run(f'oc get project "{namespace}" 2>/dev/null', check=False).returncode != 0:
        run.run(f'oc new-project "{namespace}" --skip-config-write >/dev/null')
    else:
        logging.warning(f"Project {namespace} already exists.")
        (env.ARTIFACT_DIR / "MCAD_PROJECT_ALREADY_EXISTS").touch()


def cleanup_mcad_test():
    namespace = config.ci_artifacts.get_config("tests.mcad.namespace")
    run.run(f"oc delete namespace '{namespace}' --ignore-not-found")


def prepare_cluster_scale():
    worker_label = config.ci_artifacts.get_config("clusters.sutest.worker.label")
    if run.run(f"oc get nodes -oname -l{worker_label}", capture_stdout=True).stdout:
        logging.info(f"Cluster already has {worker_label} nodes. Not applying the labels.")
    else:
        run.run(f"oc label nodes -lnode-role.kubernetes.io/worker {worker_label}")

    run.run("./run_toolbox.py from_config cluster fill_workernodes")

    run.run(f"./run_toolbox.py from_config cluster set_scale")


@entrypoint()
def prepare_ci():
    """
    Prepares the cluster and the namespace for running the tests
    """

    odh_namespace = config.ci_artifacts.get_config("odh.namespace")
    if run.run(f'oc get project -oname "{odh_namespace}" 2>/dev/null', check=False).returncode != 0:
        run.run(f'oc new-project "{odh_namespace}" --skip-config-write >/dev/null')
    else:
        logging.warning(f"Project {odh_namespace} already exists.")
        (env.ARTIFACT_DIR / "ODH_PROJECT_ALREADY_EXISTS").touch()

    for operator in config.ci_artifacts.get_config("odh.operators"):
        run.run(f"./run_toolbox.py cluster deploy_operator {operator['catalog']} {operator['name']} {operator['namespace']}")

    for resource in config.ci_artifacts.get_config("odh.kfdefs"):
        run.run(f"oc apply -f {resource}  -n {odh_namespace}")

    prepare_mcad_test()

    run.run("./run_toolbox.py from_config rhods wait_odh")

    prepare_cluster_scale()


def _run_test(test_artifact_dir_p):
    next_count = env.next_artifact_index()
    with env.TempArtifactDir(env.ARTIFACT_DIR / f"{next_count:03d}__mcad_load_test"):
        test_artifact_dir_p[0] = env.ARTIFACT_DIR

        with open(env.ARTIFACT_DIR / "settings", "w") as f:
            print(f"mcad_load_test=true", file=f)

        with open(env.ARTIFACT_DIR / "config.yaml", "w") as f:
            yaml.dump(config.ci_artifacts.config, f, indent=4)

        run.run("./run_toolbox.py cluster reset_prometheus_db > /dev/null")

        failed = True
        try:
            run.run("./run_toolbox.py from_config codeflare generate_mcad_load")

            failed = False
        finally:
            with open(env.ARTIFACT_DIR / "exit_code", "w") as f:
                print("1" if failed else "0", file=f)

            run.run("./run_toolbox.py cluster dump_prometheus_db >/dev/null")
            run.run("./run_toolbox.py cluster capture_environment >/dev/null")

    run.run("./run_toolbox.py codeflare generate_mcad_load mcad-load-test --job-mode=True")


@entrypoint()
def test_ci():
    """
    Runs the test from the CI
    """

    try:
        test_artifact_dir_p = [None]
        _run_test(test_artifact_dir_p)
    finally:
        generate_reports = config.ci_artifacts.get_config("matbench.generate_reports")
        if generate_reports and test_artifact_dir_p[0] is not None:
            next_count = env.next_artifact_index()
            with env.TempArtifactDir(env.ARTIFACT_DIR / f"{next_count:03d}__plots"):
                visualize.prepare_matbench()
                generate_plots(test_artifact_dir_p[0])
        elif not generate_reports:
            logging.warning("Not generating the visualization because it is disabled in the configuration file.")
        else:
            logging.warning("Not generating the visualization as the test artifact directory hasn't been created.")

        if config.ci_artifacts.get_config("clusters.cleanup_on_exit"):
            cleanup_cluster()


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

    odh_namespace = config.ci_artifacts.get_config("odh.namespace")

    for resource in config.ci_artifacts.get_config("odh.kfdefs"):
        run.run(f"oc delete -f {resource}  -n {odh_namespace}")

    for operator in config.ci_artifacts.get_config("odh.operators"):
        ns = "openshift-operators" if operator['namespace'] == "all" else operator['namespace']
        run.run(f"oc delete sub {operator['name']} -n {ns}")
        run.run(f"oc delete csv -loperators.coreos.com/{operator['name']}.{ns}= -n {ns}")

    run.run(f"oc delete ns {odh_namespace}")


    cleanup_mcad_test()


@entrypoint(ignore_secret_path=True)
def generate_plots(results_dirname):
    visualize.generate_from_dir(str(results_dirname))


# ---

class Entrypoint:
    """
    Commands for launching the CI tests
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
