import pathlib
import logging

from . import run

TESTING_COMMON_DIR = pathlib.Path(__file__).absolute().parent
TESTING_UTILS_DIR = TESTING_COMMON_DIR.parent / "utils"

RHODS_OPERATOR_MANIFEST_NAME = "rhods-operator"

def _setup_brew_registry(token_file):
    brew_setup_script = TESTING_UTILS_DIR / "brew.registry.redhat.io" / "setup.sh"

    return run.run(f'"{brew_setup_script}" "{token_file}"')

# ---

def install(token_file=None, force=False):
    installed_csv_cmd = run.run("oc get csv -oname -n redhat-ods-operator", capture_stdout=True)

    if not force and RHODS_OPERATOR_MANIFEST_NAME in installed_csv_cmd.stdout:
        logging.info(f"Operator '{RHODS_OPERATOR_MANIFEST_NAME}' is already installed.")
        return

    if token_file:
        _setup_brew_registry(token_file)

    run.run("./run_toolbox.py from_config rhods deploy_ods")

def uninstall():
    installed_csv_cmd = run.run("oc get csv -oname -n redhat-ods-operator", capture_stdout=True)

    if RHODS_OPERATOR_MANIFEST_NAME not in installed_csv_cmd.stdout:
        logging.info("RHODS is not installed.")
        return

    print("Force delete RHODS (workaround for RHODS-8002)")
    run.run("./run_toolbox.py rhods delete_ods > /dev/null")
    #run(f"./run_toolbox.py rhods undeploy_ods > /dev/null")


def uninstall_ldap():
    ldap_installed_cmd = run.run("oc get ns/openldap --ignore-not-found -oname", capture_stdout=True)

    if "openldap" not in ldap_installed_cmd.stdout:
        logging.info("OpenLDAP is not installed")
        return

    run.run("./run_toolbox.py from_config cluster undeploy_ldap > /dev/null")
