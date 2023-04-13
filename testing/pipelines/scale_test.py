#!/usr/bin/env python3

import sys, os
import pathlib
import subprocess
import fire
import logging
logging.getLogger().setLevel(logging.INFO)
import datetime
import time

import yaml
import jsonpath_ng

def run(command):
    logging.info(f"run: {command}")

    return subprocess.run(command, check=True, shell=True)

TESTING_PIPELINES_DIR = pathlib.Path(__file__).absolute().parent
TESTING_ODS_DIR = TESTING_PIPELINES_DIR.parent / "ods"
PSAP_ODS_SECRET_PATH = pathlib.Path(os.environ["PSAP_ODS_SECRET_PATH"])

try:
    ARTIFACT_DIR = pathlib.Path(os.environ["ARTIFACT_DIR"])
except KeyError:
    env_ci_artifact_base_dir = pathlib.Path(os.environ.get("CI_ARTIFACT_BASE_DIR", "/tmp"))
    ARTIFACT_DIR = env_ci_artifact_base_dir / f"ci-artifacts_{time.strftime('%Y%m%d')}"
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

os.environ["CI_ARTIFACTS_FROM_COMMAND_ARGS_FILE"] = str(TESTING_PIPELINES_DIR / "command_args.yaml")
os.environ["CI_ARTIFACTS_FROM_CONFIG_FILE"] = str(TESTING_PIPELINES_DIR / "config.yaml")

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
        proc = subprocess.run(f'./run_toolbox.py from_config "{command}" --show_args "{args}"', check=True, shell=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        logging.error(e.stderr.decode("utf-8").strip())
        raise

    return proc.stdout.decode("utf-8").strip()

# ---

def setup_brew_registry():
    token_file = PSAP_ODS_SECRET_PATH / get_config("secrets.brew_registry_redhat_io_token_file")

    brew_setup_script = TESTING_ODS_DIR / "brew.registry.redhat.io" / "setup.sh"

    return run(f'"{brew_setup_script}" "{token_file}"')

# ---

def install_rhods():

    try:
        run("oc get csv -n redhat-ods-operator -oname | grep rhods-operator --quiet")
        logging.warning("RHODS is already installed, do not reinstall it.")
        return
    except Exception: pass # RHODS isn't installed, proceed


    setup_brew_registry()

    run("./run_toolbox.py from_config rhods deploy_ods")


def customize_rhods():
    if get_config("rhods.operator.stop"):
        run("oc scale deploy/rhods-operator --replicas=0 -n redhat-ods-operator")
        time.sleep(10)

        dashboard_replicas = get_config("rhods.operator.dashboard.replicas")

        if dashboard_replicas is not None:
            run(f'oc scale deploy/rhods-dashboard "--replicas={dashboard_replicas}" -n redhat-ods-applications')
            with open(ARTIFACT_DIR / "dashboard.replicas", "w") as f:
                print(f"{dashboard_replicas}", file=f)

def install_ocp_pipelines():
    run("ARTIFACT_TOOLBOX_NAME_SUFFIX=_pipelines ./run_toolbox.py cluster deploy_operator redhat-operators openshift-pipelines-operator-rh all")


def create_dsp_application():
    namespace = get_config("rhods.pipelines.namespace")
    try:
        run(f'oc new-project "{namespace}" --skip-config-write >/dev/null')
    except Exception: pass # project already exists


    run("./run_toolbox.py from_config pipelines deploy_application")

def pipelines_prepare():
    """
    Prepares the cluster for running pipelines scale tests.
    """

    install_rhods()
    run("./run_toolbox.py rhods wait_ods")
    customize_rhods()
    run("./run_toolbox.py rhods wait_ods")

    install_ocp_pipelines()

    create_dsp_application()


    return None


def pipelines_run():
    """
    Runs a CI workload.

    """

    pass


class Pipelines:
    """
    Commands for launching the Pipeline Perf & Scale tests
    """

    def __init__(self):
        self.prepare = pipelines_prepare
        self.run = pipelines_run

        self.prepare_ci = pipelines_prepare
        self.test_ci = pipelines_run

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
