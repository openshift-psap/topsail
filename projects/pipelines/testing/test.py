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

from topsail.testing import env, config, run, rhods, visualize, sizing

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
    config.init(TESTING_THIS_DIR)

    if apply_preset_from_pr_args:
        config.ci_artifacts.apply_preset_from_pr_args()

    if not ignore_secret_path and not PSAP_ODS_SECRET_PATH.exists():
        raise RuntimeError("Path with the secrets (PSAP_ODS_SECRET_PATH={PSAP_ODS_SECRET_PATH}) does not exists.")

    server_url = run.run("oc whoami --show-server", capture_stdout=True).stdout.strip()

    if server_url.endswith("apps.bm.example.com:6443") or "kubernetes.default" in server_url:
        ICELAKE_PROFILE = "icelake"
        logging.info(f"Running in the Icelake cluster, applying the '{ICELAKE_PROFILE}' profile")
        config.ci_artifacts.apply_preset(ICELAKE_PROFILE)

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
    run.run(f"oc delete tektonconfigs.operator.tekton.dev --all")
    PIPELINES_OPERATOR_NAMESPACE = "openshift-operators"
    run.run(f"oc delete sub/{PIPELINES_OPERATOR_MANIFEST_NAME} -n {PIPELINES_OPERATOR_NAMESPACE} --ignore-not-found")
    run.run(f"oc delete csv -n {PIPELINES_OPERATOR_NAMESPACE} -loperators.coreos.com/{PIPELINES_OPERATOR_MANIFEST_NAME}.{PIPELINES_OPERATOR_NAMESPACE}")


    webhooks_cmd = run.run("oc get validatingwebhookconfigurations,mutatingwebhookconfigurations -oname | grep tekton.dev", capture_stdout=True, check=False)
    for webhook in webhooks_cmd.stdout.split("\n"):
        if not webhook: continue # empty lines
        run.run(f"oc delete {webhook}")


def create_dsp_application():
    run.run_toolbox_from_config("pipelines", "deploy_application")


@entrypoint()
def prepare_rhods():
    """
    Prepares the cluster for running RHODS pipelines scale tests.
    """
    install_ocp_pipelines()

    token_file = PSAP_ODS_SECRET_PATH / config.ci_artifacts.get_config("secrets.brew_registry_redhat_io_token_file")
    rhods.install(token_file)

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

    if sutest:
        # must match 'roles/local_ci_run_multi/templates/job.yaml.j2'
        cpu_count = 1
        memory = 2

    kwargs = dict(
        cpu = cpu_count,
        memory = memory,
        machine_type = config.ci_artifacts.get_config("clusters.create.ocp.compute.type"),
        user_count = config.ci_artifacts.get_config("tests.pipelines.user_count")
        )

    return sizing.main(**kwargs)


def apply_prefer_pr():
    if not config.ci_artifacts.get_config("base_image.repo.ref_prefer_pr"):
        return

    pr_number = None

    if os.environ.get("OPENSHIFT_CI"):
        pr_number = os.environ.get("PULL_NUMBER")
        if not pr_number:
            logging.warning("apply_prefer_pr: OPENSHIFT_CI: base_image.repo.ref_prefer_pr is set but PULL_NUMBER is empty")
            return

    if os.environ.get("PERFLAB_CI"):
        git_ref = os.environ.get("PERFLAB_GIT_REF")

        try:
            pr_number = int(re.compile("refs/pull/([0-9]+)/merge").match(git_ref).groups()[0])
        except Exception as e:
            logging.warning("apply_prefer_pr: PERFLAB_CI: base_image.repo.ref_prefer_pr is set cannot parse PERFLAB_GIT_REF={git_erf}: {e.__class__.__name__}: {e}")
            return

    if not pr_number:
        logging.warning("apply_prefer_pr: Could not figure out the PR number. Keeping the default value.")
        return

    pr_ref = f"refs/pull/{pr_number}/merge"

    logging.info(f"Setting '{pr_ref}' as ref for building the base image")
    config.ci_artifacts.set_config("base_image.repo.ref", pr_ref)
    config.ci_artifacts.set_config("base_image.repo.tag", f"pr-{pr_number}")

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

    create_dsp_application()


@entrypoint()
def prepare_test_driver_namespace():
    """
    Prepares the cluster for running the multi-user ci-artifacts operations
    """

    namespace = config.ci_artifacts.get_config("base_image.namespace")
    service_account = config.ci_artifacts.get_config("base_image.user.service_account")
    role = config.ci_artifacts.get_config("base_image.user.role")

    #
    # Prepare the driver namespace
    #

    if run.run(f'oc get project "{namespace}" 2>/dev/null', check=False).returncode != 0:
        run.run(f'oc new-project "{namespace}" --skip-config-write >/dev/null')
    else:
        logging.warning(f"Project {namespace} already exists.")
        (env.ARTIFACT_DIR / "PROJECT_ALREADY_EXISTS").touch()

    dedicated = "{}" if config.ci_artifacts.get_config("clusters.driver.compute.dedicated") \
        else '{value: ""}' # delete the toleration/node-selector annotations, if it exists

    run.run_toolbox_from_config("cluster", "set_project_annotation", prefix="driver", suffix="test_node_selector", extra=dedicated)
    run.run_toolbox_from_config("cluster", "set_project_annotation", prefix="driver", suffix="test_toleration", extra=dedicated)

    #
    # Prepare the driver machineset
    #

    if not config.ci_artifacts.get_config("clusters.driver.is_metal"):
        nodes_count = config.ci_artifacts.get_config("clusters.driver.compute.machineset.count")
        extra = dict()
        if nodes_count is None:
            node_count = compute_node_requirement(driver=True)
            extra["scale"] = node_count

        run.run_toolbox_from_config("cluster", "set_scale", prefix="driver", extra=extra)

    #
    # Prepare the container image
    #

    istag = config.get_command_arg("cluster", "build_push_image --prefix base_image", "_istag")

    if run.run(f"oc get istag {istag} -n {namespace} -oname 2>/dev/null", check=False).returncode == 0:
        logging.info(f"Image {istag} already exists in namespace {namespace}. Don't build it.")
    else:
        run.run_toolbox_from_config("cluster", "build_push_image", prefix="base_image")

    #
    # Deploy Redis server for Pod startup synchronization
    #

    run.run_toolbox_from_config("cluster", "deploy_redis_server")

    #
    # Deploy Minio
    #

    run.run_toolbox_from_config(f"cluster", "deploy_minio_s3_server")

    #
    # Prepare the ServiceAccount
    #

    run.run(f"oc create serviceaccount {service_account} -n {namespace} --dry-run=client -oyaml | oc apply -f-")
    run.run(f"oc adm policy add-cluster-role-to-user {role} -z {service_account} -n {namespace}")

    #
    # Prepare the Secret
    #

    secret_name = config.ci_artifacts.get_config("secrets.dir.name")
    secret_env_key = config.ci_artifacts.get_config("secrets.dir.env_key")

    run.run(f"oc create secret generic {secret_name} --from-file=$(echo ${secret_env_key}/* | tr ' ' ,) -n {namespace} --dry-run=client -oyaml | oc apply -f-")


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
    apply_prefer_pr()

    with run.Parallel("prepare_cluster") as parallel:
        parallel.delayed(prepare_test_driver_namespace)
        parallel.delayed(prepare_sutest_scale_up)
        parallel.delayed(prepare_rhods)


@entrypoint()
def pipelines_run_one():
    """
    Runs a single Pipeline scale test.
    """

    if job_index := os.environ.get("JOB_COMPLETION_INDEX"):
        namespace = config.ci_artifacts.get_config("rhods.pipelines.namespace")
        new_namespace = f"{namespace}-user-{job_index}"
        logging.info(f"Running in a parallel job. Changing the pipeline test namespace to '{new_namespace}'")
        config.ci_artifacts.set_config("rhods.pipelines.namespace", new_namespace)

    try:
        prepare_pipelines_namespace()
        run.run_toolbox_from_config("pipelines", "run_kfp_notebook")
    finally:
        run.run_toolbox_from_config("pipelines", "capture_state", mute_stdout=True)


@entrypoint()
def pipelines_run_many():
    """
    Runs multiple concurrent Pipelines scale test.
    """
    _not_used__test_artifact_dir_p = [None]
    _pipelines_run_many(_not_used__test_artifact_dir_p)

@entrypoint()
def pipelines_run_stress():
    """
    Runs stress test of pipelines
    """
    _not_used__test_artifact_dir_p = [None]
    _pipelines_run_many(_not_used__test_artifact_dir_p)

@entrypoint()
def pipelines_run_mixed():
    """
    Runs a mixed workload composed of various pipelines
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
def cleanup_sutest_ns():
    """
    Cleans up the SUTest namespaces
    """

    cleanup_scale_test()


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

    rhods.uninstall()

    #
    # uninstall LDAP
    #

    rhods.uninstall_ldap()

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

    apply_prefer_pr()

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
