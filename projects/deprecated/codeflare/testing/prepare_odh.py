import logging
import pathlib

from projects.core.library import env, config, run

def prepare_odh():
    odh_namespace = config.project.get_config("odh.namespace")
    if run.run(f'oc get project -oname "{odh_namespace}" 2>/dev/null', check=False).returncode != 0:
        run.run(f'oc new-project "{odh_namespace}" --skip-config-write >/dev/null')
    else:
        logging.warning(f"Project {odh_namespace} already exists.")
        (env.ARTIFACT_DIR / "ODH_PROJECT_ALREADY_EXISTS").touch()

    for operator in config.project.get_config("odh.operators"):
        run.run_toolbox("cluster", "deploy_operator", catalog=operator['catalog'], manifest_name=operator['name'], namespace=operator['namespace'], artifact_dir_suffix=operator['catalog'])

    for resource in config.project.get_config("odh.kfdefs"):
        if not resource.startswith("http"):
            run.run(f"oc apply -f {resource} -n {odh_namespace}")
            continue

        filename = "kfdef__" + pathlib.Path(resource).name

        run.run(f"curl -Ssf {resource} | tee '{env.ARTIFACT_DIR / filename}' | oc apply -f- -n {odh_namespace}")

    run.run_toolbox_from_config("rhods", "wait_odh")


def prepare_odh_customization():
    odh_stopped = False
    customized = False
    if config.project.get_config("odh.customize.operator.stop"):
        logging.info("Stopping the ODH operator ...")
        run.run("oc scale deploy/codeflare-operator-manager --replicas=0 -n openshift-operators")
        odh_stopped = True

    if config.project.get_config("odh.customize.mcad.controller_image.enabled"):
        if not odh_stopped:
            raise RuntimeError("Cannot customize MCAD controller image if the ODH operator isn't stopped ...")
        customized = True

        odh_namespace = config.project.get_config("odh.namespace")
        image = config.project.get_config("odh.customize.mcad.controller_image.image")
        tag = config.project.get_config("odh.customize.mcad.controller_image.tag")
        logging.info(f"Setting MCAD controller image to {image}:{tag} ...")
        run.run(f"oc set image deploy/mcad-controller-mcad mcad-controller={image}:{tag} -n {odh_namespace}")

        run.run("oc delete appwrappers -A --all # delete all appwrappers")
        run.run("oc delete crd appwrappers.workload.codeflare.dev")
        run.run("oc apply -f https://raw.githubusercontent.com/project-codeflare/multi-cluster-app-dispatcher/main/config/crd/bases/workload.codeflare.dev_appwrappers.yaml")

    if customized:
        run.run_toolbox_from_config("rhods", "wait_odh")


def cleanup_odh():
    odh_namespace = config.project.get_config("odh.namespace")

    has_kfdef = run.run("oc get kfdef -n not-a-namespace --ignore-not-found", check=False).returncode == 0
    if has_kfdef:
        for resource in config.project.get_config("odh.kfdefs"):
            run.run(f"oc delete -f {resource} --ignore-not-found -n {odh_namespace}")
    else:
        logging.info("Cluster doesn't know the Kfdef CRD, skipping KFDef deletion")

    for operator in config.project.get_config("odh.operators"):
        ns = "openshift-operators" if operator['namespace'] == "all" else operator['namespace']
        run.run(f"oc delete sub {operator['name']} -n {ns} --ignore-not-found ")
        run.run(f"oc delete csv -loperators.coreos.com/{operator['name']}.{ns}= -n {ns} --ignore-not-found ")
