#!/usr/bin/env python3

import sys, os
import pathlib
import subprocess
import fire
import logging
logging.getLogger().setLevel(logging.INFO)
import datetime
import time
import shutil

import yaml
import jsonpath_ng

PIPELINES_OPERATOR_MANIFEST_NAME = "openshift-pipelines-operator-rh"
RHODS_OPERATOR_MANIFEST_NAME = "rhods-operator"

def run(command, capture_stdout=False, capture_stderr=False, check=True):
    logging.info(f"run: {command}")
    args = {}
    if capture_stdout: args["stdout"] = subprocess.PIPE
    if capture_stderr: args["stderr"] = subprocess.PIPE
    if check: args["check"] = True

    proc = subprocess.run(command, shell=True, **args)

    if capture_stdout: proc.stdout = proc.stdout.decode("utf8")
    if capture_stderr: proc.stderr = proc.stderr.decode("utf8")

    return proc

TESTING_PIPELINES_DIR = pathlib.Path(__file__).absolute().parent
TESTING_UTILS_DIR = TESTING_PIPELINES_DIR.parent / "utils"
PSAP_ODS_SECRET_PATH = pathlib.Path(os.environ["PSAP_ODS_SECRET_PATH"])

try:
    ARTIFACT_DIR = pathlib.Path(os.environ["ARTIFACT_DIR"])
except KeyError:
    env_ci_artifact_base_dir = pathlib.Path(os.environ.get("CI_ARTIFACT_BASE_DIR", "/tmp"))
    ARTIFACT_DIR = env_ci_artifact_base_dir / f"ci-artifacts_{time.strftime('%Y%m%d')}"
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)


def set_config_environ():
    os.environ["CI_ARTIFACTS_FROM_COMMAND_ARGS_FILE"] = str(TESTING_PIPELINES_DIR / "command_args.yaml")
    config_path = ARTIFACT_DIR / "config.yaml"
    os.environ["CI_ARTIFACTS_FROM_CONFIG_FILE"] = str(config_path)

    # make sure we're using a clean copy of the configuration file
    config_path.unlink(missing_ok=True)

    if shared_dir := os.environ.get("SHARED_DIR"):
        shared_dir_config_path = pathlib.Path(shared_dir) / "config.yaml"
        if shared_dir_config_path.exists():
            logging.info(f"Reloading the config file from {shared_dir_config_path} ...")
            shutil.copyfile(shared_dir_config_path, config_path)

    if not config_path.exists():
        shutil.copyfile(TESTING_PIPELINES_DIR / "config.yaml", config_path)


set_config_environ()
with open(os.environ["CI_ARTIFACTS_FROM_CONFIG_FILE"]) as config_f:
    config = yaml.safe_load(config_f)


def get_config(jsonpath):
    try:
        value = jsonpath_ng.parse(jsonpath).find(config)[0].value
    except Exception as ex:
        logging.error(f"get_config: {jsonpath} --> {ex}")
        raise ex

    logging.info(f"get_config: {jsonpath} --> {value}")

    return value


def get_command_arg(command, args):
    try:
        logging.info(f"get_command_arg: {command} {args}")
        proc = subprocess.run(f'./run_toolbox.py from_config {command} --show_args "{args}"', check=True, shell=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        logging.error(e.stderr.decode("utf-8").strip())
        raise

    return proc.stdout.decode("utf-8").strip()


def set_config(jsonpath, value):
    try:
        jsonpath_ng.parse(jsonpath).update(config, value)
    except Exception as ex:
        logging.error(f"set_config: {jsonpath}={value} --> {ex}")
        raise

    logging.info(f"set_config: {jsonpath} --> {value}")

    with open(os.environ["CI_ARTIFACTS_FROM_CONFIG_FILE"], "w") as f:
        yaml.dump(config, f, indent=4)

    if (shared_dir := os.environ.get("SHARED_DIR")) and (shared_dir_path := pathlib.Path(shared_dir)) and shared_dir_path.exists():

        with open(shared_dir_path / "config.yaml", "w") as f:
            yaml.dump(config, f, indent=4)

# ---

def setup_brew_registry():
    token_file = PSAP_ODS_SECRET_PATH / get_config("secrets.brew_registry_redhat_io_token_file")

    brew_setup_script = TESTING_UTILS_DIR / "brew.registry.redhat.io" / "setup.sh"

    return run(f'"{brew_setup_script}" "{token_file}"')

# ---

def install_rhods():
    installed_csv_cmd = run("oc get csv -oname -n redhat-ods-operator", capture_stdout=True)

    if RHODS_OPERATOR_MANIFEST_NAME in installed_csv_cmd.stdout:
        logging.info(f"Operator '{RHODS_OPERATOR_MANIFEST_NAME}' is already installed.")
        return

    setup_brew_registry()

    run("./run_toolbox.py from_config rhods deploy_ods")


def customize_rhods():
    if not get_config("rhods.operator.stop"):
        return

    run("oc scale deploy/rhods-operator --replicas=0 -n redhat-ods-operator")
    time.sleep(10)


def install_ocp_pipelines():
    installed_csv_cmd = run("oc get csv -oname", capture_stdout=True)
    if PIPELINES_OPERATOR_MANIFEST_NAME in installed_csv_cmd.stdout:
        logging.info(f"Operator '{PIPELINES_OPERATOR_MANIFEST_NAME}' is already installed.")
        return

    run(f"ARTIFACT_TOOLBOX_NAME_SUFFIX=_pipelines ./run_toolbox.py cluster deploy_operator redhat-operators {PIPELINES_OPERATOR_MANIFEST_NAME} all")


def create_dsp_application():
    namespace = get_config("rhods.pipelines.namespace")
    try:
        run(f'oc new-project "{namespace}" --skip-config-write >/dev/null')
    except Exception: pass # project already exists

    label_key = get_config("rhods.pipelines.namespace_label.key")
    label_value = get_config("rhods.pipelines.namespace_label.value")
    run(f"oc label 'ns/{namespace}' '{label_key}={label_value}' --overwrite")

    run("./run_toolbox.py from_config pipelines deploy_application")


def prepare_rhods():
    """
    Prepares the cluster for running RHODS pipelines scale tests.
    """
    install_ocp_pipelines()
    install_rhods()

    run("./run_toolbox.py rhods wait_ods")
    customize_rhods()
    run("./run_toolbox.py rhods wait_ods")

    run("./run_toolbox.py from_config cluster deploy_ldap")

    run("./run_toolbox.py from_config cluster set_scale --prefix=sutest")


def prepare_pipelines_namespace():
    """
    Prepares the namespace for running a pipelines scale test.
    """

    namespace = get_config("rhods.pipelines.namespace")
    run(f"oc new-project '{namespace}' --skip-config-write >/dev/null 2>/dev/null || true")
    run(f"oc label namespace/{namespace} opendatahub.io/dashboard=true --overwrite")

    dedicated = "{}" if get_config("clusters.sutest.compute.dedicated") \
        else '{value: ""}' # delete the toleration/node-selector annotations, if it exists

    run(f"./run_toolbox.py from_config cluster set_project_annotation --prefix sutest --suffix pipelines_node_selector --extra '{dedicated}'")
    run(f"./run_toolbox.py from_config cluster set_project_annotation --prefix sutest --suffix pipelines_toleration --extra '{dedicated}'")

    create_dsp_application()


def prepare_test_driver_namespace():
    """
    Prepares the cluster for running the multi-user ci-artifacts operations
    """

    namespace = get_config("base_image.namespace")
    service_account = get_config("base_image.user.service_account")
    role = get_config("base_image.user.role")

    #
    # Prepare the container image
    #

    if get_config("base_image.repo.ref_prefer_pr") and (pr_number := os.environ.get("PULL_NUMBER")):
        pr_ref = f"refs/pull/{pr_number}/head"

        logging.info(f"Setting '{pr_ref}' as ref for building the base image")
        set_config("base_image.repo.ref", pr_ref)
        set_config("base_image.repo.tag", f"pr-{pr_number}")

    # keep this command (utils build_push_image) first, it creates the namespace

    istag = get_command_arg("utils build_push_image --prefix base_image", "_istag")
    try:
        run(f"oc get istag {istag} -n {namespace} -oname 2>/dev/null")
        has_istag = True
        logging.info(f"Image {istag} already exists in namespace {namespace}. Don't build it.")
    except subprocess.CalledProcessError:
        has_istag = False

    if not has_istag:
        run(f"./run_toolbox.py from_config utils build_push_image --prefix base_image")

    #
    # Deploy Redis server for Pod startup synchronization
    #

    run("./run_toolbox.py from_config cluster deploy_redis_server")

    #
    # Deploy Minio
    #

    run(f"./run_toolbox.py from_config cluster deploy_minio_s3_server")

    #
    # Prepare the ServiceAccount
    #

    run(f"oc create serviceaccount {service_account} -n {namespace} --dry-run=client -oyaml | oc apply -f-")
    run(f"oc adm policy add-cluster-role-to-user {role} -z {service_account} -n {namespace}")

    #
    # Prepare the Secret
    #

    secret_name = get_config("secrets.dir.name")
    secret_env_key = get_config("secrets.dir.env_key")

    run(f"oc create secret generic {secret_name} --from-file=$(echo ${secret_env_key}/* | tr ' ' ,) -n {namespace} --dry-run=client -oyaml | oc apply -f-")


def pipelines_prepare_cluster():
    """
    Prepares the cluster and the namespace for running pipelines scale tests
    """

    prepare_test_driver_namespace()
    prepare_rhods()


def pipelines_run_one():
    """
    Runs a single Pipeline scale test.
    """

    if job_index := os.environ.get("JOB_COMPLETION_INDEX"):
        namespace = get_config("rhods.pipelines.namespace")
        new_namespace = f"{namespace}-user-{job_index}"
        logging.info(f"Running in a parallel job. Changing the pipeline test namespace to '{new_namespace}'")
        set_config("rhods.pipelines.namespace", new_namespace)

    try:
        prepare_pipelines_namespace()
        run(f"./run_toolbox.py from_config pipelines run_kfp_notebook")
    finally:
        run(f"./run_toolbox.py from_config pipelines capture_state")


def pipelines_run_many():
    """
    Runs multiple concurrent Pipelines scale test.
    """

    run(f"./run_toolbox.py from_config pipelines run_scale_test")


def pipelines_cleanup_scale_test():
    """
    Cleanups the pipelines scale test namespaces
    """

    #
    # delete the pipelines namespaces
    #
    label_key = get_config("rhods.pipelines.namespace_label.key")
    label_value = get_config("rhods.pipelines.namespace_label.value")
    run(f"oc delete ns -l{label_key}={label_value} --ignore-not-found")

def pipelines_cleanup_cluster():
    """
    Restores the cluster to its original state
    """

    pipelines_cleanup_scale_test()

    #
    # uninstall RHODS
    #
    installed_csv_cmd = run("oc get csv -oname -n redhat-ods-operator", capture_stdout=True)

    if RHODS_OPERATOR_MANIFEST_NAME in installed_csv_cmd.stdout:
        run(f"./run_toolbox.py rhods undeploy_ods > /dev/null")
    else:
        logging.info("RHODS is not installed.")
    #
    # uninstall the pipelines operator
    #
    installed_csv_cmd = run("oc get csv -oname", capture_stdout=True)
    if PIPELINES_OPERATOR_MANIFEST_NAME in installed_csv_cmd.stdout:
        run(f"oc delete tektonconfigs.operator.tekton.dev --all")
        PIPELINES_OPERATOR_NAMESPACE = "openshift-operators"
        run(f"oc delete sub/{PIPELINES_OPERATOR_MANIFEST_NAME} -n {PIPELINES_OPERATOR_NAMESPACE}")
        run(f"oc delete csv -n {PIPELINES_OPERATOR_NAMESPACE} -loperators.coreos.com/{PIPELINES_OPERATOR_MANIFEST_NAME}.{PIPELINES_OPERATOR_NAMESPACE}")
    else:
        logging.info("Pipelines Operator is not installed")
    #
    # uninstall LDAP
    #
    ldap_installed_cmd = run("oc get ns/openldap --ignore-not-found -oname", capture_stdout=True)
    if "openldap" in ldap_installed_cmd.stdout:
        run("./run_toolbox.py from_config cluster undeploy_ldap > /dev/null")
    else:
        logging.info("OpenLDAP is not installed")

    #
    # delete the test driver namespace
    #
    base_image_ns = get_config("base_image.namespace")
    run(f"oc delete ns '{base_image_ns}' --ignore-not-found")

def pipelines_test_ci():
    """
    Runs the Pipelines scale test from the CI
    """

    try:
        pipelines_run_many()
    finally:
        if get_config("clusters.cleanup_on_exit"):
            pipelines_cleanup_cluster()

class Pipelines:
    """
    Commands for launching the Pipeline Perf & Scale tests
    """

    def __init__(self):
        self.prepare_cluster = pipelines_prepare_cluster
        self.prepare_rhods = prepare_rhods
        self.prepare_pipelines_namespace = prepare_pipelines_namespace
        self.prepare_test_driver_namespace = prepare_test_driver_namespace

        self.run_one = pipelines_run_one
        self.run = pipelines_run_many

        self.cleanup_cluster = pipelines_cleanup_cluster
        self.cleanup_scale_test = pipelines_cleanup_scale_test

        self.prepare_ci = pipelines_prepare_cluster
        self.test_ci = pipelines_test_ci


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
