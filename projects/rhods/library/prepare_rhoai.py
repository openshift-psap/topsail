import pathlib
import logging

from projects.core.library import run, config, env

TOPSAIL_DIR = pathlib.Path(config.__file__).parents[3]

RHODS_OPERATOR_MANIFEST_NAME = "rhods-operator"

def _setup_brew_registry(token_file):
    brew_setup_script = TOPSAIL_DIR / "projects" / "rhods" / "utils" / "brew.registry.redhat.io" / "setup.sh"

    return run.run(f'"{brew_setup_script}" "{token_file}"')

# ---

def install_servicemesh():
    run.run_toolbox("cluster", "deploy_operator",
                    catalog="redhat-operators",
                    manifest_name="servicemeshoperator",
                    namespace="all",
                    artifact_dir_suffix="_service-mesh")


def install(token_file=None, force=False):
    installed_csv_cmd = run.run("oc get csv -oname -n redhat-ods-operator", capture_stdout=True)

    if not force and RHODS_OPERATOR_MANIFEST_NAME in installed_csv_cmd.stdout:
        logging.info(f"Operator '{RHODS_OPERATOR_MANIFEST_NAME}' is already installed.")
        return

    if token_file:
        _setup_brew_registry(token_file)

    with env.NextArtifactDir("install_rhoai"):
        install_servicemesh()
        run.run_toolbox_from_config("rhods", "deploy_ods")


def uninstall(mute=True):
    installed_csv_cmd = run.run("oc get csv -oname -n redhat-ods-operator", capture_stdout=True)

    if RHODS_OPERATOR_MANIFEST_NAME not in installed_csv_cmd.stdout:
        logging.info("RHODS is not installed.")
        # make sure that no core RHODS namespace is still there
        run.run('oc get ns redhat-ods-applications redhat-ods-monitoring redhat-ods-operator --ignore-not-found')
    else:
        if run.run(f'oc get datasciencecluster -oname | grep .', check=False).returncode == 0:
            run.run_toolbox("rhods", "update_datasciencecluster")

        run.run_toolbox("rhods", "undeploy_ods", mute_stdout=mute)

    uninstall_servicemesh(mute)


def uninstall_ldap(mute=True):
    ldap_installed_cmd = run.run("oc get ns/openldap --ignore-not-found -oname", capture_stdout=True)

    if "openldap" not in ldap_installed_cmd.stdout:
        logging.info("OpenLDAP is not installed")
        return

    run.run_toolbox_from_config("cluster", "undeploy_ldap", mute_stdout=mute)


def uninstall_servicemesh(mute=True):
    operator = dict(
        name = "servicemeshoperator",
        namespace = "all",
    )
    cleanup = dict(
        namespaces = ["istio-system"],
        crds = [
            "servicemeshmemberrolls.maistra.io",
            "servicemeshcontrolplanes.maistra.io",
        ],
    )

    manifest_name = operator["name"]
    namespace = "openshift-operators"

    for crd in cleanup.get("crds", []):
        run.run(f"oc delete {crd} --all -A", check=False)

    installed_csv_cmd = run.run(f"oc get csv -oname -n {namespace} "
                                f"-loperators.coreos.com/{manifest_name}.{namespace}", capture_stdout=mute)

    if not installed_csv_cmd.stdout:
        logging.info(f"{manifest_name} operator is not installed")

    run.run(f"oc delete sub/{manifest_name} -n {namespace} --ignore-not-found")
    run.run(f"oc delete csv -n {namespace} -loperators.coreos.com/{manifest_name}.{namespace}")

    for crd in cleanup.get("crds", []):
        run.run(f"oc delete crd/{crd} --ignore-not-found")

    for ns in cleanup.get("namespaces", []):
        run.run(f"timeout 300 oc delete ns {ns} --ignore-not-found")
