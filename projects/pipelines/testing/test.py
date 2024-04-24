#!/usr/bin/env python

import sys, os
import pathlib
import subprocess
import logging
logging.getLogger().setLevel(logging.INFO)
import datetime
import time
import functools
import re
import uuid

import yaml
import fire

from projects.core.library import env, config, run, visualize, sizing
from projects.rhods.library import prepare_rhoai
from projects.local_ci.library import prepare_user_pods

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

def customize_rhods():
    if not config.ci_artifacts.get_config("rhods.operator.stop"):
        return

    run.run("oc scale deploy/rhods-operator --replicas=0 -n redhat-ods-operator")
    time.sleep(10)


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


def create_dsp_application():
    run.run_toolbox_from_config("pipelines", "deploy_application")


@entrypoint()
def prepare_rhods():
    """
    Prepares the cluster for running RHODS pipelines scale tests.
    """
    install_ocp_pipelines()

    token_file = PSAP_ODS_SECRET_PATH / config.ci_artifacts.get_config("secrets.brew_registry_redhat_io_token_file")
    prepare_rhoai.install(token_file)

    has_dsc = run.run("oc get dsc -oname", capture_stdout=True).stdout

    run.run_toolbox("rhods", "update_datasciencecluster", enable=["datasciencepipelines", "workbenches"],
                    name=None if has_dsc else "default-dsc")
    customize_rhods()

    run.run_toolbox_from_config("cluster", "deploy_ldap")


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
        machine_type = config.ci_artifacts.get_config("clusters.driver.compute.machineset.type")

    if sutest:
        # must match 'roles/local_ci_run_multi/templates/job.yaml.j2'
        cpu_count = 1
        memory = 2
        machine_type = config.ci_artifacts.get_config("clusters.sutest.compute.machineset.type")

    kwargs = dict(
        cpu = cpu_count,
        memory = memory,
        machine_type = machine_type,
        user_count = config.ci_artifacts.get_config("tests.pipelines.user_count")
        )

    return sizing.main(**kwargs)


@entrypoint()
def prepare_pipelines_namespace():
    """
    Prepares the namespace for running a pipelines scale test.
    """

    namespace = config.ci_artifacts.get_config("rhods.pipelines.namespace")
    if run.run(f'oc get project "{namespace}" 2>/dev/null', check=False).returncode != 0:
        run.run(f'oc new-project "{namespace}" --skip-config-write >/dev/null')
    else:
        logging.warning(f"Project {namespace} already exists.")
        (env.ARTIFACT_DIR / "PROJECT_ALREADY_EXISTS").touch()

    run.run(f"oc label namespace/{namespace} opendatahub.io/dashboard=true --overwrite")

    label_key = config.ci_artifacts.get_config("rhods.pipelines.namespace_label.key")
    label_value = config.ci_artifacts.get_config("rhods.pipelines.namespace_label.value")
    run.run(f"oc label namespace/{namespace} '{label_key}={label_value}' --overwrite")

    dedicated = "{}" if config.ci_artifacts.get_config("clusters.sutest.compute.dedicated") \
        else '{value: ""}' # delete the toleration/node-selector annotations, if it exists

    run.run_toolbox_from_config("cluster", "set_project_annotation", prefix="sutest", suffix="pipelines_node_selector", extra=dedicated)
    run.run_toolbox_from_config("cluster", "set_project_annotation", prefix="sutest", suffix="pipelines_toleration" , extra=dedicated)


@entrypoint()
def prepare_test_driver_namespace():
    """
    Prepares the cluster for running the multi-user ci-artifacts operations
    """

    user_count = config.ci_artifacts.get_config("tests.pipelines.user_count")
    with run.Parallel("prepare_driver") as parallel:

        parallel.delayed(prepare_user_pods.prepare_user_pods, user_count)
        parallel.delayed(prepare_user_pods.cluster_scale_up, user_count)


@entrypoint()
def prepare_sutest_scale_up():
    """
    Scales up the SUTest cluster with the right number of nodes
    """

    if config.ci_artifacts.get_config("clusters.sutest.is_metal"):
        return

    node_count = config.ci_artifacts.get_config("clusters.sutest.compute.machineset.count")
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

    with run.Parallel("prepare_cluster") as parallel:
        parallel.delayed(prepare_test_driver_namespace)
        parallel.delayed(prepare_sutest_scale_up)
        parallel.delayed(prepare_rhods)


@entrypoint()
def pipelines_run_one():
    """
    Runs a single Pipeline scale test.
    """

    project_count = config.ci_artifacts.get_config("tests.pipelines.project_count")
    user_count = config.ci_artifacts.get_config("tests.pipelines.user_count")
    pipelines_per_user = config.ci_artifacts.get_config("tests.pipelines.pipelines_per_user")

    uid = -1
    if user_index := os.environ.get("JOB_COMPLETION_INDEX"):
        uid = user_index

        namespace = config.ci_artifacts.get_config("rhods.pipelines.namespace")
        ns_index = int(user_index) % int(project_count)
        new_namespace = f"{namespace}-n{ns_index}"
        logging.info(f"Running in a parallel job. Changing the pipeline test namespace to '{new_namespace}'")
        config.ci_artifacts.set_config("rhods.pipelines.namespace", new_namespace)
        application_name = f"user{user_index}-sample"
        config.ci_artifacts.set_config("rhods.pipelines.application.name", application_name)

    try:

        prepare_pipelines_namespace()
        create_dsp_application()

        if not config.ci_artifacts.get_config("tests.pipelines.deploy_pipeline"):
            return

        user_pipeline_delay = int(config.ci_artifacts.get_config("tests.pipelines.user_pipeline_delay"))
        for pipeline_num in range(pipelines_per_user):
            logging.info(f"Running run_kfp_notebook for pipeline {pipeline_num}")
            notebook_name = f"user{uid}-run{pipeline_num}"
            run.run_toolbox_from_config("pipelines", "run_kfp_notebook", extra={"notebook_name": notebook_name})
            if pipeline_num != pipelines_per_user - 1:
                time.sleep(user_pipeline_delay)

    finally:
        run.run_toolbox_from_config("pipelines", "capture_state", mute_stdout=True)


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
            yaml.dump(config.ci_artifacts.config, f, indent=4)

        with open(env.ARTIFACT_DIR / ".uuid", "w") as f:
            print(str(uuid.uuid4()), file=f)

        user_count = config.ci_artifacts.get_config("tests.pipelines.user_count")
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

                run.run_toolbox("notebooks", "capture_state", mute_stdout=True, check=False)

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
    label_key = config.ci_artifacts.get_config("rhods.pipelines.namespace_label.key")
    label_value = config.ci_artifacts.get_config("rhods.pipelines.namespace_label.value")
    run.run(f"oc delete ns -l{label_key}={label_value} --ignore-not-found")


@entrypoint()
def cleanup_cluster():
    """
    Restores the cluster to its original state
    """

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
    base_image_ns = config.ci_artifacts.get_config("base_image.namespace")
    run.run(f"oc delete ns '{base_image_ns}' --ignore-not-found")


@entrypoint()
def test_ci():
    """
    Runs the Pipelines scale test from the CI
    """

    cleanup_scale_test()
    prepare_user_pods.apply_prefer_pr()

    try:
        test_artifact_dir_p = [None]
        try:
            _pipelines_run_many(test_artifact_dir_p)
        finally:
            if test_artifact_dir_p[0] is not None:
                next_count = env.next_artifact_index()
                with env.TempArtifactDir(env.ARTIFACT_DIR / f"{next_count:03d}__plots"):
                    visualize.prepare_matbench()
                    generate_plots(test_artifact_dir_p[0])
            else:
                logging.warning("Not generating the visualization as the test artifact directory hasn't been created.")

    finally:
        if config.ci_artifacts.get_config("clusters.cleanup_on_exit"):
            pipelines_cleanup_cluster()

@entrypoint(ignore_secret_path=True, apply_preset_from_pr_args=False)
def generate_plots_from_pr_args():
    visualize.download_and_generate_visualizations()


@entrypoint(ignore_secret_path=True)
def generate_plots(results_dirname):
    visualize.generate_from_dir(str(results_dirname))

@entrypoint()
def rebuild_driver_image(pr_number):
    namespace = config.ci_artifacts.get_config("base_image.namespace")
    prepare_user_pods.rebuild_driver_image(namespace, pr_number)

class Pipelines:
    """
    Commands for launching the Pipeline Perf & Scale tests
    """

    def __init__(self):
        self.prepare_cluster = prepare_cluster
        self.prepare_rhods = prepare_rhods
        self.prepare_pipelines_namespace = prepare_pipelines_namespace
        self.prepare_test_driver_namespace = prepare_test_driver_namespace
        self.prepare_sutest_scale_up = prepare_sutest_scale_up
        self.rebuild_driver_image = rebuild_driver_image

        self.run_one = pipelines_run_one
        self.run = pipelines_run_many

        self.cleanup_cluster = cleanup_cluster
        self.cleanup_cluster_ci = cleanup_cluster

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
