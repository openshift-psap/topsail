import pathlib
import logging

from . import run

TOPSAIL_TESTING_DIR = pathlib.Path(__file__).absolute().parent
TOPSAIL_DIR = TOPSAIL_TESTING_DIR.parent.parent
TESTING_UTILS_DIR = TOPSAIL_DIR / "testing" / "utils"

RHODS_OPERATOR_MANIFEST_NAME = "rhods-operator"

def _setup_brew_registry(token_file):
    brew_setup_script = TESTING_UTILS_DIR / "brew.registry.redhat.io" / "setup.sh"

    return run.run(f'"{brew_setup_script}" "{token_file}"')

# ---

def install_servicemesh():
    run.run_toolbox("cluster", "deploy_operator",
                    catalog="redhat-operators",
                    manifest_name="servicemeshoperator",
                    namespace="all",
                    artifact_dir_suffix="servicemesh")


def install(token_file=None, force=False):
    installed_csv_cmd = run.run("oc get csv -oname -n redhat-ods-operator", capture_stdout=True)

    if not force and RHODS_OPERATOR_MANIFEST_NAME in installed_csv_cmd.stdout:
        logging.info(f"Operator '{RHODS_OPERATOR_MANIFEST_NAME}' is already installed.")
        return

    if token_file:
        _setup_brew_registry(token_file)

    install_servicemesh()

    run.run_toolbox_from_config("rhods", "deploy_ods")


def uninstall(mute=True):
    installed_csv_cmd = run.run("oc get csv -oname -n redhat-ods-operator", capture_stdout=True)

    if RHODS_OPERATOR_MANIFEST_NAME not in installed_csv_cmd.stdout:
        logging.info("RHODS is not installed.")
        # make sure that no core RHODS namespace is still there
        run.run('oc get ns redhat-ods-applications redhat-ods-monitoring redhat-ods-operator --ignore-not-found')
        return

    if run.run(f'oc get datasciencecluster -oname | grep .', check=False).returncode == 0:
        run.run_toolbox("rhods", "update_datasciencecluster")

    run.run_toolbox("rhods", "undeploy_ods", mute_stdout=mute)


def uninstall_ldap(mute=True):
    ldap_installed_cmd = run.run("oc get ns/openldap --ignore-not-found -oname", capture_stdout=True)

    if "openldap" not in ldap_installed_cmd.stdout:
        logging.info("OpenLDAP is not installed")
        return

    run.run_toolbox_from_config("cluster", "undeploy_ldap", mute_stdout=mute)
