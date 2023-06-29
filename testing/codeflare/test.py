#!/usr/bin/env python3

import sys, os
import pathlib
import subprocess
import logging
logging.getLogger().setLevel(logging.INFO)
import datetime
import time
import functools
import traceback
import copy

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


def prepare_worker_node_labels():
    worker_label = config.ci_artifacts.get_config("clusters.sutest.worker.label")
    if run.run(f"oc get nodes -oname -l{worker_label}", capture_stdout=True).stdout:
        logging.info(f"Cluster already has {worker_label} nodes. Not applying the labels.")
    else:
        run.run(f"oc label nodes -lnode-role.kubernetes.io/worker {worker_label}")


def prepare_gpu_operator():
    run.run("./run_toolbox.py nfd_operator deploy_from_operatorhub")
    run.run("./run_toolbox.py gpu_operator deploy_from_operatorhub")
    run.run("./run_toolbox.py from_config gpu_operator enable_time_sharing")


def cleanup_gpu_operator():
    if run.run(f'oc get project -oname nvidia-gpu-operator 2>/dev/null', check=False).returncode != 0:
        run.run("oc delete ns nvidia-gpu-operator")
        run.run("oc delete clusterpolicy --all")

    if run.run(f'oc get project -oname openshift-nfd 2>/dev/null', check=False).returncode != 0:
        run.run("oc delete ns openshift-nfd")


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

    if config.ci_artifacts.get_config("tests.mcad.want_gpu"):
        prepare_gpu_operator()

    prepare_worker_node_labels()

    if config.ci_artifacts.get_config("tests.mcad.want_gpu"):
        run.run("./run_toolbox.py from_config gpu_operator run_gpu_burn")

    if config.ci_artifacts.get_config("clusters.sutest.worker.fill_resources.enabled"):
        namespace = config.ci_artifacts.get_config("clusters.sutest.worker.fill_resources.namespace")
        if run.run(f'oc get project "{namespace}" 2>/dev/null', check=False).returncode != 0:
            run.run(f'oc new-project "{namespace}" --skip-config-write >/dev/null')

        run.run("./run_toolbox.py from_config cluster fill_workernodes")


def save_matbench_files(name, cfg):
    with open(env.ARTIFACT_DIR / "settings", "w") as f:
        print(f"mcad_load_test=true", file=f)
        print(f"name={name}", file=f)

    with open(env.ARTIFACT_DIR / "config.yaml", "w") as f:
        yaml.dump(config.ci_artifacts.config, f, indent=4)

    with open(env.ARTIFACT_DIR / "test_case_config.yaml", "w") as f:
        yaml.dump(cfg, f)


def _prepare_test_nodes(name, cfg, dry_mode):
    extra = {}

    extra["instance_type"] = cfg["node"]["instance_type"]
    extra["scale"] = cfg["node"]["count"]

    if dry_mode:
        logging.info(f"dry_mode: scale up the cluster for the test '{name}': {extra} ")
        return

    run.run(f"./run_toolbox.py from_config cluster set_scale --extra \"{extra}\"")

    if cfg["node"].get("wait_gpus", True):
        if not config.ci_artifacts.get_config("tests.mcad.want_gpu"):
            logging.error("Cannot wait for GPUs when tests.mcad.want_gpu is disabled ...")
        else:
            run.run("./run_toolbox.py gpu_operator wait_stack_deployed")


def merge(a, b, path=None):
    "updates a with b"
    if path is None: path = []
    for key in b:
        if key in a and isinstance(a[key], dict) and isinstance(b[key], dict):
            merge(a[key], b[key], path + [str(key)])
        else:
            a[key] = b[key]
    return a

def _run_test(name, test_artifact_dir_p):
    dry_mode = config.ci_artifacts.get_config("tests.mcad.dry_mode")
    capture_prom = config.ci_artifacts.get_config("tests.mcad.capture_prom")
    prepare_nodes = config.ci_artifacts.get_config("tests.mcad.prepare_nodes")

    test_templates = config.ci_artifacts.get_config("tests.mcad.test_templates")

    parents_to_apply = [name]
    cfg = {"templates": []}
    while parents_to_apply:
        template_name = parents_to_apply.pop()
        cfg["templates"].insert(0, template_name)
        logging.info(f"Applying test template {template_name} ...")
        try:
            test_template = test_templates[template_name]
        except KeyError:
            logging.error(f"Test template {template_name} does not exist. Available templates: {', '.join(test_templates.keys())}")
            raise
        cfg = merge(copy.deepcopy(test_template), cfg)
        if "extends" in cfg:
            parents_to_apply += cfg["extends"]
            del cfg["extends"]

    logging.info("Test configuration: \n"+yaml.dump(cfg))

    next_count = env.next_artifact_index()
    with env.TempArtifactDir(env.ARTIFACT_DIR / f"{next_count:03d}__prepare"):
        if prepare_nodes:
            _prepare_test_nodes(name, cfg, dry_mode)
        else:
            logging.info("tests.mcad.prepare_nodes=False, skipping.")

        if not dry_mode and capture_prom:
            run.run("./run_toolbox.py cluster reset_prometheus_db > /dev/null")

    next_count = env.next_artifact_index()
    with env.TempArtifactDir(env.ARTIFACT_DIR / f"{next_count:03d}__mcad_load_test"):

        test_artifact_dir_p[0] = env.ARTIFACT_DIR
        save_matbench_files(name, cfg)

        extra = {}
        failed = True
        try:
            configs = [
                ("states", "target"),
                ("states", "unexpected"),
                ("job", "template_name"),
                ("pod", "count"),
                ("pod", "runtime"),
                ("pod", "requests"),
            ]

            for (group, key) in configs:
                if not key in cfg["aw"].get(group, {}): continue
                extra[f"{group}_{key}"] = cfg["aw"][group][key]

            extra["aw_base_name"] = name
            extra["timespan"] = cfg["timespan"]
            extra["aw_count"] = cfg["aw"]["count"]
            extra["timespan"] = cfg["timespan"]

            job_mode = cfg["aw"]["job"].get("run_job_mode")

            if dry_mode:
                logging.info(f"Running the load test '{name}' with {extra}. Do job_mode: {job_mode} ...")
                return

            load_test_failed = False
            job_load_test_failed = False
            try:
                run.run(f"./run_toolbox.py from_config codeflare generate_mcad_load --extra \"{extra}\"")
            except Exception as e:
                load_test_failed = True

            if job_mode:
                extra["job_mode"] = True
                logging.info("Running in Job mode ...")
                try:
                    run.run(f"ARTIFACT_TOOLBOX_NAME_PREFIX=job_mode_ ./run_toolbox.py from_config codeflare generate_mcad_load --extra \"{extra}\"")
                except Exception as e:
                    job_load_test_failed = True

            failed = load_test_failed or job_load_test_failed
        finally:
            with open(env.ARTIFACT_DIR / "exit_code", "w") as f:
                print("1" if failed else "0", file=f)

            if not dry_mode:
                if capture_prom:
                    run.run("./run_toolbox.py cluster dump_prometheus_db >/dev/null")

                # must be part of the test directory
                run.run("./run_toolbox.py cluster capture_environment >/dev/null")


def _run_test_and_visualize(name):
    try:
        test_artifact_dir_p = [None]
        _run_test(name, test_artifact_dir_p)
    finally:
        dry_mode = config.ci_artifacts.get_config("tests.mcad.dry_mode")
        if not config.ci_artifacts.get_config("tests.mcad.visualize"):
            logging.info(f"Visualization disabled.")

        elif dry_mode:
            logging.info(f"Running in dry mode, skipping the visualization.")

        elif test_artifact_dir_p[0] is not None:
            next_count = env.next_artifact_index()
            with env.TempArtifactDir(env.ARTIFACT_DIR / f"{next_count:03d}__plots"):
                visualize.prepare_matbench()
                generate_plots(test_artifact_dir_p[0])
        else:
            logging.warning("Not generating the visualization as the test artifact directory hasn't been created.")


@entrypoint()
def test_ci(name=None, dry_mode=False, visualize=True, capture_prom=True, prepare_nodes=True):
    """
    Runs the test from the CI

    Args:
      name: name of the test to run. If empty, run all the tests of the configuration file
      dry_mode: if True, do not execute the tests, only list what would be executed
      visualize: if False, do not generate the visualization reports
      capture_prom: if False, do not capture Prometheus database
      prepare_nodes: if False, do not scale up the cluster nodes
    """


    config.ci_artifacts.set_config("tests.mcad.dry_mode", dry_mode)
    config.ci_artifacts.set_config("tests.mcad.visualize", visualize)
    config.ci_artifacts.set_config("tests.mcad.capture_prom", capture_prom)
    config.ci_artifacts.set_config("tests.mcad.prepare_nodes", prepare_nodes)

    try:
        failed_tests = []
        ex = None
        tests_to_run = config.ci_artifacts.get_config("tests.mcad.tests_to_run") \
            if not name else [name]

        for name in tests_to_run:

            next_count = env.next_artifact_index()
            with env.TempArtifactDir(env.ARTIFACT_DIR / f"{next_count:03d}_test-case_{name}"):
                try:
                    _run_test_and_visualize(name)
                except Exception as e:
                    ex = e
                    failed_tests.append(name)
                    logging.error(f"*** Caught an exception during test {name}: {e.__class__.__name__}: {e}")
                    traceback.print_exc()

                    with open(env.ARTIFACT_DIR / "FAILURE", "w") as f:
                        print(traceback.format_exc(), file=f)

                    import bdb
                    if isinstance(e, bdb.BdbQuit):
                        raise

        if failed_tests:
            with open(env.ARTIFACT_DIR / "FAILED_TESTS", "w") as f:
                print("\n".join(failed_tests), file=f)

            logging.error(f"Caught exception(s) in [{', '.join(failed_tests)}], aborting.")

            raise ex
    finally:
        run.run(f"testing/utils/generate_plot_index.py > {env.ARTIFACT_DIR}/report_index.html", check=False)

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

    fill_namespace = config.ci_artifacts.get_config("clusters.sutest.worker.fill_resources.namespace")

    run.run(f"oc delete ns {odh_namespace} {fill_namespace} --ignore-not-found")

    cleanup_mcad_test()

    if config.ci_artifacts.get_config("tests.mcad.want_gpu"):
        cleanup_gpu_operator()


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
