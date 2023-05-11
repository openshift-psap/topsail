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
TESTING_ODS_DIR = TESTING_PIPELINES_DIR.parent / "ods"
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

# ---

def setup_brew_registry():
    token_file = PSAP_ODS_SECRET_PATH / get_config("secrets.brew_registry_redhat_io_token_file")

    brew_setup_script = TESTING_ODS_DIR / "brew.registry.redhat.io" / "setup.sh"

    return run(f'"{brew_setup_script}" "{token_file}"')

# ---

def install_rhods():
    MANIFEST_NAME = "rhods-operator"
    installed_csv_cmd = run("oc get csv -oname -n redhat-ods-operator", capture_stdout=True)

    if MANIFEST_NAME in installed_csv_cmd.stdout:
        logging.info(f"Operator '{MANIFEST_NAME}' is already installed.")
        return

    setup_brew_registry()

    run("./run_toolbox.py from_config rhods deploy_ods")


def customize_rhods():
    if not get_config("rhods.operator.stop"):
        return

    run("oc scale deploy/rhods-operator --replicas=0 -n redhat-ods-operator")
    time.sleep(10)

    dashboard_commit = get_config("rhods.operator.dashboard.custom_commit")
    if dashboard_commit:
        dashboard_image = "quay.io/opendatahub/odh-dashboard:main-" + dashboard_commit
        run(f"oc set image deploy/rhods-dashboard 'rhods-dashboard={dashboard_image}' -n redhat-ods-applications")

    if get_config("rhods.operator.dashboard.enable_pipelines"):
        # Update CRD OdhDashboardConfigs to enable data science
        crd_url = f"https://raw.githubusercontent.com/opendatahub-io/odh-dashboard/{dashboard_commit}/manifests/crd/odhdashboardconfigs.opendatahub.io.crd.yaml"
        run(f"oc apply -f {crd_url}")

        # Enable pipelines in Dashboard
        run("""oc patch OdhDashboardConfig/odh-dashboard-config -n redhat-ods-applications --type=merge --patch='{"spec":{"dashboardConfig":{"disablePipelines":false}}}'""")

    dashboard_replicas = get_config("rhods.operator.dashboard.replicas")
    if dashboard_replicas is not None:
        run(f'oc scale deploy/rhods-dashboard "--replicas={dashboard_replicas}" -n redhat-ods-applications')
        with open(ARTIFACT_DIR / "dashboard.replicas", "w") as f:
            print(f"{dashboard_replicas}", file=f)

def install_ocp_pipelines():
    MANIFEST_NAME = "openshift-pipelines-operator-rh"
    installed_csv_cmd = run("oc get csv -oname", capture_stdout=True)
    if MANIFEST_NAME in installed_csv_cmd.stdout:
        logging.info(f"Operator '{MANIFEST_NAME}' is already installed.")
        return

    run(f"ARTIFACT_TOOLBOX_NAME_SUFFIX=_pipelines ./run_toolbox.py cluster deploy_operator redhat-operators {MANIFEST_NAME} all")

def create_dsp_application():
    namespace = get_config("rhods.pipelines.namespace")
    try:
        run(f'oc new-project "{namespace}" --skip-config-write >/dev/null')
    except Exception: pass # project already exists


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


def prepare_namespace():
    """
    Prepares the namespace for running a pipelines scale test.
    """

    namespace = get_config("rhods.pipelines.namespace")
    run(f"oc new-project '{namespace}' --skip-config-write >/dev/null || true")
    run(f"oc label namespace/{namespace} opendatahub.io/dashboard=true --overwrite")

    dedicated = "{}" if get_config("clusters.sutest.compute.dedicated") \
        else '{value: ""}' # delete the toleration/node-selector annotations, if it exists

    run(f"./run_toolbox.py from_config cluster set_project_annotation --prefix sutest --suffix pipelines_node_selector --extra '{dedicated}'")
    run(f"./run_toolbox.py from_config cluster set_project_annotation --prefix sutest --suffix pipelines_toleration --extra '{dedicated}'")

    create_dsp_application()


def build_base_image():
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
    run(f"oc get secrets -n {namespace}")

def pipelines_prepare():
    """
    Prepares the cluster and the namespace for running pipelines scale tests
    """

    build_base_image()
    prepare_rhods()


def pipelines_run_one():
    """
    Runs a single Pipeline scale test.
    """

    try:
        prepare_namespace()
        run(f"./run_toolbox.py from_config pipelines run_kfp_notebook")
    finally:
        run(f"./run_toolbox.py from_config pipelines capture_state")

def pipelines_run_many():
    """
    Runs multiple concurrent Pipelines scale test.
    """

    run(f"./run_toolbox.py from_config local_ci run --suffix scale_test")

class Pipelines:
    """
    Commands for launching the Pipeline Perf & Scale tests
    """

    def __init__(self):
        self.prepare = pipelines_prepare
        self.prepare_rhods = prepare_rhods
        self.prepare_namespace = prepare_namespace
        self.build_base_image = build_base_image

        self.run_one = pipelines_run_one
        self.run = pipelines_run_many

        self.prepare_ci = pipelines_prepare
        self.test_ci = self.run

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
