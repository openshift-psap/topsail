import pathlib
import logging

from projects.core.library import run, config, env

TOPSAIL_DIR = pathlib.Path(config.__file__).parents[3]

RHODS_OPERATOR_MANIFEST_NAME = "rhods-operator"
RHODS_NAMESPACE = "redhat-ods-operator"
def _setup_brew_registry(token_file):
    brew_setup_script = TOPSAIL_DIR / "projects" / "rhods" / "utils" / "brew.registry.redhat.io" / "setup.sh"

    return run.run(f'"{brew_setup_script}" "{token_file}"')

# ---

def install_servicemesh():
    SERVICE_MESH_MANIFEST_NAME = "servicemeshoperator"
    installed_csv_cmd = run.run("oc get csv -oname -n openshift-operators", capture_stdout=True)

    if SERVICE_MESH_MANIFEST_NAME in installed_csv_cmd.stdout:
        logging.info(f"Operator '{SERVICE_MESH_MANIFEST_NAME}' is already installed.")
        return

    run.run_toolbox("cluster", "deploy_operator",
                    catalog="redhat-operators",
                    manifest_name=SERVICE_MESH_MANIFEST_NAME,
                    namespace="all",
                    artifact_dir_suffix="_service-mesh")


def is_rhoai_installed():
    installed_csv_cmd = run.run(f"oc get csv -loperators.coreos.com/{RHODS_OPERATOR_MANIFEST_NAME}.{RHODS_NAMESPACE}"
                                f" -n {RHODS_NAMESPACE}", capture_stdout=True, capture_stderr=True)

    return "No resources found" not in installed_csv_cmd.stderr


def install(token_file=None, force=False):
    if is_rhoai_installed():
        logging.info(f"Operator '{RHODS_OPERATOR_MANIFEST_NAME}' is already installed.")

        if not force:
            return

    if token_file:
        _setup_brew_registry(token_file)

    with env.NextArtifactDir("install_rhoai"):
        install_servicemesh()
        run.run_toolbox_from_config("rhods", "deploy_ods")


def uninstall(mute=True):
    if not is_rhoai_installed():
        logging.info("RHODS is not installed.")
        # make sure that no core RHODS namespace is still there
        run.run(f"oc get ns redhat-ods-applications redhat-ods-monitoring {RHODS_NAMESPACE} --ignore-not-found")
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

    run.run_toolbox_from_config("server", "undeploy_ldap", mute_stdout=mute)


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
                                f"-loperators.coreos.com/{manifest_name}.{namespace}", capture_stdout=True)

    if not installed_csv_cmd.stdout:
        logging.info(f"{manifest_name} operator is not installed")
        return

    run.run(f"oc delete sub/{manifest_name} -n {namespace} --ignore-not-found")
    run.run(f"oc delete csv -n {namespace} -loperators.coreos.com/{manifest_name}.{namespace}")
    run.run(f"oc delete installplan -n {namespace} -loperators.coreos.com/{manifest_name}.{namespace}")

    for crd in cleanup.get("crds", []):
        run.run(f"oc delete crd/{crd} --ignore-not-found")

    for ns in cleanup.get("namespaces", []):
        run.run(f"timeout 300 oc delete ns {ns} --ignore-not-found")

def is_component_deployed(component: str):
    is_deployed = run.run(f"oc get dsc -ojsonpath='{{.items[0].status.installedComponents.{component}}}'", check=False, capture_stdout=True).stdout == "true"

    return is_deployed
