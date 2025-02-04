#!/usr/bin/env python

import sys, os
import pathlib
import subprocess
import logging
import datetime
import time
import functools
import re
import uuid

import json
import yaml
import fire

from projects.core.library import env, config, run, sizing, common, configure_logging
configure_logging()
from projects.rhods.library import prepare_rhoai
from projects.local_ci.library import prepare_user_pods
from projects.matrix_benchmarking.library import visualize

PIPELINES_OPERATOR_MANIFEST_NAME = "openshift-pipelines-operator-rh"

TESTING_THIS_DIR = pathlib.Path(__file__).absolute().parent
TESTING_UTILS_DIR = TESTING_THIS_DIR.parent / "utils"

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

def rhoai_down():
    # Pause RHOAI by scaling replicas -> 0
    if run.run(f'oc get deploy/rhods-operator -n redhat-ods-operator 2>/dev/null', check=False).returncode == 0:
        run.run("oc patch deployment.apps/rhods-operator -n redhat-ods-operator --type merge -p '{\"spec\": {\"replicas\": 0}}'")
        run.run("oc wait --for jsonpath='{.spec.replicas}'=0 deployment.apps/rhods-operator -n redhat-ods-operator --timeout=5m")

def rhoai_up():
    # Resume RHOAI by scaling replicas -> 1
    if run.run(f'oc get deploy/rhods-operator -n redhat-ods-operator 2>/dev/null', check=False).returncode == 0:
        run.run("oc patch deployment.apps/rhods-operator -n redhat-ods-operator --type merge -p '{\"spec\": {\"replicas\": 1}}'")
        run.run("oc wait --for jsonpath='{.status.availableReplicas}'=1 deployment.apps/rhods-operator -n redhat-ods-operator --timeout=5m")

def install_ocp_pipelines():
    installed_csv_cmd = run.run("oc get csv -oname", capture_stdout=True)
    if PIPELINES_OPERATOR_MANIFEST_NAME in installed_csv_cmd.stdout:
        logging.info(f"Operator '{PIPELINES_OPERATOR_MANIFEST_NAME}' is already installed.")
        return

    run.run_toolbox("cluster", "deploy_operator", catalog="redhat-operators", manifest_name=PIPELINES_OPERATOR_MANIFEST_NAME, namespace="all", artifact_dir_suffix=f"_{PIPELINES_OPERATOR_MANIFEST_NAME}")


def uninstall_ocp_pipelines():
    PIPELINES_OPERATOR_NAMESPACE = "openshift-operators"
    run.run(f"oc delete sub/{PIPELINES_OPERATOR_MANIFEST_NAME} -n {PIPELINES_OPERATOR_NAMESPACE} --ignore-not-found")
    run.run(f"oc delete csv -n {PIPELINES_OPERATOR_NAMESPACE} -loperators.coreos.com/{PIPELINES_OPERATOR_MANIFEST_NAME}.{PIPELINES_OPERATOR_NAMESPACE}")


def create_dsp_application(dspa_name):
    old_dspa_name = config.project.get_config("rhods.pipelines.application.name")
    config.project.set_config("rhods.pipelines.application.name", dspa_name)
    if run.run(f'oc get dspa/"{dspa_name}" 2>/dev/null', check=False).returncode != 0:
        run.run_toolbox_from_config("pipelines", "deploy_application")
    config.project.set_config("rhods.pipelines.application.name", old_dspa_name)

@entrypoint()
def prepare_rhods():
    """
    Prepares the cluster for running RHODS pipelines scale tests.
    """

    token_file = PSAP_ODS_SECRET_PATH / config.project.get_config("secrets.rhoai_token_file")
    prepare_rhoai.install(token_file)

    has_dsc = run.run("oc get dsc -oname", capture_stdout=True).stdout

    run.run_toolbox("rhods", "update_datasciencecluster", enable=["datasciencepipelines", "workbenches"],
                    name=None if has_dsc else "default-dsc")

    run.run_toolbox_from_config("server", "deploy_ldap")

    install_ocp_pipelines()


def compute_node_requirement(driver=False, sutest=False):
    if (not driver and not sutest) or (sutest and driver):
        raise ValueError("compute_node_requirement must be called with driver=True or sutest=True")

    if driver:
        # from the right namespace, get a hint of the resource request with these commands:
        # oc get pods -oyaml | yq .items[].spec.containers[].resources.requests.cpu -r | awk NF | grep -v null | python -c "import sys; print(sum(int(l.strip()[:-1]) for l in sys.stdin))"
        # --> 1090
        # oc get pods -oyaml | yq .items[].spec.containers[].resources.requests.memory -r | awk NF | grep -v null | python -c "import sys; print(sum(int(l.strip()[:-2]) for l in sys.stdin))"
        # --> 2668
        cpu_count = 1.5
        memory = 3
        machine_type = config.project.get_config("clusters.driver.compute.machineset.type")

    if sutest:
        # must match 'projects/local_ci/toolbox/local_ci_run_multi/templates/job.yaml.j2'
        cpu_count = 2
        memory = 4
        machine_type = config.project.get_config("clusters.sutest.compute.machineset.type")

    kwargs = dict(
        cpu = cpu_count,
        memory = memory,
        machine_type = machine_type,
        user_count = config.project.get_config("tests.pipelines.user_count")
        )

    return sizing.main(**kwargs)


def prepare_project(namespace, dspa_name):
    """
    Prepares the namespace for running a pipelines scale test.
    """
    old_namespace = config.project.get_config("rhods.pipelines.namespace")
    config.project.set_config("rhods.pipelines.namespace", namespace)
    if run.run(f'oc get project "{namespace}" 2>/dev/null', check=False).returncode != 0:
        run.run(f'oc new-project "{namespace}" --skip-config-write >/dev/null')
    else:
        logging.warning(f"Project {namespace} already exists.")
        (env.ARTIFACT_DIR / "PROJECT_ALREADY_EXISTS").touch()

    run.run(f"oc label namespace/{namespace} opendatahub.io/dashboard=true --overwrite")

    label_key = config.project.get_config("rhods.pipelines.namespace_label.key")
    label_value = config.project.get_config("rhods.pipelines.namespace_label.value")
    run.run(f"oc label namespace/{namespace} '{label_key}={label_value}' --overwrite")

    dedicated = "{}" if config.project.get_config("clusters.sutest.compute.dedicated") \
        else '{value: ""}' # delete the toleration/node-selector annotations, if it exists

    run.run_toolbox_from_config("cluster", "set_project_annotation", prefix="sutest", suffix="pipelines_node_selector", extra=dedicated)
    run.run_toolbox_from_config("cluster", "set_project_annotation", prefix="sutest", suffix="pipelines_toleration" , extra=dedicated)

    create_dsp_application(dspa_name)

    config.project.set_config("rhods.pipelines.namespace", old_namespace)

@entrypoint()
def prepare_test_driver_namespace():
    """
    Prepares the cluster for running the multi-user TOPSAIL operations
    """

    user_count = config.project.get_config("tests.pipelines.user_count")
    with run.Parallel("prepare_driver") as parallel:

        parallel.delayed(prepare_user_pods.prepare_user_pods, user_count)
        parallel.delayed(prepare_user_pods.cluster_scale_up, user_count)


@entrypoint()
def prepare_sutest_scale_up():
    """
    Scales up the SUTest cluster with the right number of nodes
    """

    if config.project.get_config("clusters.sutest.is_metal"):
        return

    node_count = config.project.get_config("clusters.sutest.compute.machineset.count")
    extra = dict()
    if node_count is None:
        node_count = compute_node_requirement(sutest=True)
        extra["scale"] = node_count

    run.run_toolbox_from_config("cluster", "set_scale", prefix="sutest", extra=extra)

@entrypoint()
def prepare_cluster():
    """
    Prepares the cluster and the namespace for running pipelines scale tests
    """
    prepare_user_pods.apply_prefer_pr()

    if config.project.get_config("clusters.create.ocp.deploy_cluster.target") == "cluster_light":
        run.run_toolbox("cluster", "wait_fully_awake")

    with run.Parallel("prepare_cluster") as parallel:
        parallel.delayed(prepare_test_driver_namespace)
        parallel.delayed(prepare_sutest_scale_up)
        parallel.delayed(prepare_rhods)

    # Update the MAX_CONCURRENT_RECONCILES if needed
    max_concurrent_reconciles = config.project.get_config("tests.pipelines.max_concurrent_reconciles")
    if max_concurrent_reconciles is not None:
        rhoai_down() # Pause RHOAI so we can edit a variable in the DSPO
        generation_cmd = run.run("oc get -ojson deployment/data-science-pipelines-operator-controller-manager -n redhat-ods-applications | jq '.status.observedGeneration' -r", capture_stdout=True)
        current_generation = int(generation_cmd.stdout)
        next_gen = current_generation + 1
        run.run(f"oc set env deployment/data-science-pipelines-operator-controller-manager MAX_CONCURRENT_RECONCILES={str(max_concurrent_reconciles)} -n redhat-ods-applications")
        # Wait for the generation to have been incremented (the controller recognizes a new
        # version is necessary), then for new replica to take over 2->1
        run.run(f"oc wait --for jsonpath='{{.status.observedGeneration}}'={str(next_gen)} deployment/data-science-pipelines-operator-controller-manager -n redhat-ods-applications --timeout=5m")
        run.run("oc wait --for jsonpath='{.status.replicas}'=1 deployment/data-science-pipelines-operator-controller-manager -n redhat-ods-applications --timeout=5m")

@entrypoint()
def pipelines_run_one():
    """
    Runs a single Pipeline scale test.
    """

    project_count = config.project.get_config("tests.pipelines.project_count")
    pipelines_per_user = config.project.get_config("tests.pipelines.pipelines_per_user")

    uid = "-1"
    if user_index := os.environ.get("JOB_COMPLETION_INDEX"):
        uid = user_index

        namespace = config.project.get_config("rhods.pipelines.namespace")
        ns_index = int(user_index) % int(project_count)
        new_namespace = f"{namespace}-n{ns_index}"
        logging.info(f"Running in a parallel job. Changing the pipeline test namespace to '{new_namespace}'")
        config.project.set_config("rhods.pipelines.namespace", new_namespace)
        application_name = f"n{ns_index}-sample"
        config.project.set_config("rhods.pipelines.application.name", application_name)

    try:

        if not config.project.get_config("tests.pipelines.deploy_pipeline"):
            return

        user_pipeline_delay = int(config.project.get_config("tests.pipelines.user_pipeline_delay"))
        for pipeline_num in range(pipelines_per_user):
            logging.info(f"Running run_kfp_notebook for pipeline {pipeline_num}")
            notebook_name = f"user{uid}-pl{pipeline_num}"
            run.run_toolbox_from_config("pipelines", "run_kfp_notebook", extra={"notebook_name": notebook_name})
            if pipeline_num != pipelines_per_user - 1:
                time.sleep(user_pipeline_delay)

    finally:
        run.run_toolbox_from_config("pipelines", "capture_state", mute_stdout=True, extra={"user_id": uid})


@entrypoint()
def pipelines_run_many():
    """
    Runs multiple concurrent Pipelines scale test.
    """
    _not_used__test_artifact_dir_p = [None]
    _pipelines_run_many(_not_used__test_artifact_dir_p)


def _pipelines_run_many(test_artifact_dir_p):
    ARTIFACTS_VERSION = "2023-06-05"

    # argument 'test_artifact_dir_p' is a pointer to
    # 'test_artifact_dir', like by-reference arguments of C the reason
    # for this C-ism is that this way, test_artifact_dir can be
    # returned to the caller even if the test fails and raises an
    # exception (so that we can run the visualization even if the test
    # failed)

    def prepare_matbench_files():
        with open(env.ARTIFACT_DIR / "config.yaml", "w") as f:
            yaml.dump(config.project.config, f, indent=4)

        with open(env.ARTIFACT_DIR / ".uuid", "w") as f:
            print(str(uuid.uuid4()), file=f)

        user_count = config.project.get_config("tests.pipelines.user_count")
        with open(env.ARTIFACT_DIR / "settings.yaml", "w") as f:
            yaml.dump(dict(user_count=user_count), f, indent=4)

        with open(env.ARTIFACT_DIR / "artifacts_version", "w") as f:
            print(ARTIFACTS_VERSION, file=f)

    next_count = env.next_artifact_index()
    test_artifact_dir_p[0] = \
        test_artifact_dir = env.ARTIFACT_DIR / f"{next_count:03d}__pipelines_run_many"
    try:
        with env.TempArtifactDir(test_artifact_dir):

            prepare_matbench_files()

            failed = True
            try:
                run.run_toolbox_from_config("local_ci", "run_multi")
                failed = False
            finally:
                with open(env.ARTIFACT_DIR / "exit_code", "w") as f:
                    print("1" if failed else "0", file=f)

                run.run_toolbox("pipelines", "capture_notebooks_state", mute_stdout=True, check=False)

    finally:
        run.run_toolbox("cluster", "capture_environment", mute_stdout=True, check=False)


@entrypoint()
def cleanup_scale_test():
    """
    Cleanups the pipelines scale test namespaces
    """

    #
    # delete the pipelines namespaces
    #
    label_key = config.project.get_config("rhods.pipelines.namespace_label.key")
    label_value = config.project.get_config("rhods.pipelines.namespace_label.value")
    run.run(f"oc delete ns -l{label_key}={label_value} --ignore-not-found")


@entrypoint()
def cleanup_cluster():
    """
    Restores the cluster to its original state
    """

    rhoai_up()
    common.cleanup_cluster()

    cleanup_scale_test()

    #
    # uninstall RHODS
    #

    prepare_rhoai.uninstall()

    #
    # uninstall LDAP
    #

    prepare_rhoai.uninstall_ldap()

    #
    # uninstall the pipelines operator
    #

    uninstall_ocp_pipelines()

    #
    # delete the test driver namespace
    #
    base_image_ns = config.project.get_config("base_image.namespace")
    run.run(f"oc delete ns '{base_image_ns}' --ignore-not-found")


@entrypoint()
def test_ci():
    """
    Runs the Pipelines scale test from the CI
    """

    cleanup_scale_test()
    prepare_user_pods.apply_prefer_pr()

    # Pre-deploy projects for all users
    num_projects = int(config.project.get_config("tests.pipelines.project_count"))
    namespace_prefix = config.project.get_config("rhods.pipelines.namespace")
    project_delay = int(config.project.get_config("tests.pipelines.sleep_factor"))
    for n in range(num_projects):
        namespace = f"{namespace_prefix}-n{n}"
        dspa_name = f"n{n}-sample"
        prepare_project(namespace, dspa_name)
        time.sleep(project_delay)

    try:
        test_artifact_dir_p = [None]
        try:
            _pipelines_run_many(test_artifact_dir_p)
        finally:
            if test_artifact_dir_p[0] is not None:
                next_count = env.next_artifact_index()
                with env.TempArtifactDir(env.ARTIFACT_DIR / f"{next_count:03d}__plots"):
                    generate_plots(test_artifact_dir_p[0])
            else:
                logging.warning("Not generating the visualization as the test artifact directory hasn't been created.")

    finally:
        if config.project.get_config("clusters.cleanup_on_exit"):
            cleanup_cluster()

@entrypoint(ignore_secret_path=True, apply_preset_from_pr_args=False)
def generate_plots_from_pr_args():
    visualize.download_and_generate_visualizations()


@entrypoint(ignore_secret_path=True)
def generate_plots(results_dirname):
    visualize.generate_from_dir(str(results_dirname))

@entrypoint()
def rebuild_driver_image(pr_number):
    namespace = config.project.get_config("base_image.namespace")
    prepare_user_pods.rebuild_driver_image(namespace, pr_number)

class Pipelines:
    """
    Commands for launching the Pipeline Perf & Scale tests
    """

    def __init__(self):
        self.prepare_cluster = prepare_cluster
        self.prepare_rhods = prepare_rhods
        self.prepare_test_driver_namespace = prepare_test_driver_namespace
        self.prepare_sutest_scale_up = prepare_sutest_scale_up
        self.rebuild_driver_image = rebuild_driver_image

        self.run_one = pipelines_run_one
        self.run = pipelines_run_many

        self.cleanup_cluster = cleanup_cluster
        self.pre_cleanup_ci = cleanup_cluster

        self.cleanup_scale_test = cleanup_scale_test

        self.prepare_ci = prepare_cluster
        self.test_ci = test_ci

        self.generate_plots = generate_plots
        self.generate_plots_from_pr_args = generate_plots_from_pr_args

def main():
    # Print help rather than opening a pager
    fire.core.Display = lambda lines, out: print(*lines, file=out)

    fire.Fire(Pipelines())


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
