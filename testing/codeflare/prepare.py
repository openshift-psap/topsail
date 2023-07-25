import logging
import pathlib

from common import env, config, run

def prepare_mcad_test():
    namespace = config.ci_artifacts.get_config("tests.mcad.namespace")
    if run.run(f'oc get project "{namespace}" 2>/dev/null', check=False).returncode != 0:
        run.run(f'oc new-project "{namespace}" --skip-config-write >/dev/null')
    else:
        logging.warning(f"Project {namespace} already exists.")
        (env.ARTIFACT_DIR / "MCAD_PROJECT_ALREADY_EXISTS").touch()


def cleanup_mcad_test():
    namespace = config.ci_artifacts.get_config("tests.mcad.namespace")
    run.run(f"oc delete namespace '{namespace}' --ignore-not-found")


def prepare_worker_node_labels():
    worker_label = config.ci_artifacts.get_config("clusters.sutest.worker.label")
    if run.run(f"oc get nodes -oname -l{worker_label}", capture_stdout=True).stdout:
        logging.info(f"Cluster already has {worker_label} nodes. Not applying the labels.")
    else:
        run.run(f"oc label nodes -lnode-role.kubernetes.io/worker {worker_label}")


def prepare_gpu_operator():
    run.run("./run_toolbox.py nfd_operator deploy_from_operatorhub")
    run.run("./run_toolbox.py gpu_operator deploy_from_operatorhub")
    run.run("./run_toolbox.py from_config gpu_operator enable_time_sharing")


def prepare_odh_customization():
    odh_stopped = False
    customized = False
    if config.ci_artifacts.get_config("odh.customize.operator.stop"):
        logging.info("Stopping the ODH operator ...")
        run.run("oc scale deploy/codeflare-operator-manager --replicas=0 -n openshift-operators")
        odh_stopped = True

    if config.ci_artifacts.get_config("odh.customize.mcad.controller_image.enabled"):
        if not odh_stopped:
            raise RuntimeError("Cannot customize MCAD controller image if the ODH operator isn't stopped ...")
        customized = True

        odh_namespace = config.ci_artifacts.get_config("odh.namespace")
        image = config.ci_artifacts.get_config("odh.customize.mcad.controller_image.image")
        tag = config.ci_artifacts.get_config("odh.customize.mcad.controller_image.tag")
        logging.info(f"Setting MCAD controller image to {image}:{tag} ...")
        run.run(f"oc set image deploy/mcad-controller-mcad mcad-controller={image}:{tag} -n {odh_namespace}")

        run.run("oc delete appwrappers -A --all # delete all appwrappers")
        run.run("oc delete crd appwrappers.mcad.ibm.com")
        run.run("oc apply -f https://raw.githubusercontent.com/project-codeflare/multi-cluster-app-dispatcher/main/config/crd/bases/mcad.ibm.com_appwrappers.yaml")

    if customized:
        run.run("./run_toolbox.py from_config rhods wait_odh")


def cleanup_gpu_operator():
    if run.run(f'oc get project -oname nvidia-gpu-operator 2>/dev/null', check=False).returncode != 0:
        run.run("oc delete ns nvidia-gpu-operator")
        run.run("oc delete clusterpolicy --all")

    if run.run(f'oc get project -oname openshift-nfd 2>/dev/null', check=False).returncode != 0:
        run.run("oc delete ns openshift-nfd")


def prepare_test_nodes(name, cfg, dry_mode):
    extra = {}

    extra["instance_type"] = cfg["node"]["instance_type"]
    extra["scale"] = cfg["node"]["count"]

    if dry_mode:
        logging.info(f"dry_mode: scale up the cluster for the test '{name}': {extra} ")
        return

    run.run(f"./run_toolbox.py from_config cluster set_scale --extra \"{extra}\"")

    if cfg["node"].get("wait_gpus", True):
        if not config.ci_artifacts.get_config("tests.want_gpu"):
            logging.error("Cannot wait for GPUs when tests.want_gpu is disabled ...")
        else:
            run.run("./run_toolbox.py gpu_operator wait_stack_deployed")


def prepare_odh():
    odh_namespace = config.ci_artifacts.get_config("odh.namespace")
    if run.run(f'oc get project -oname "{odh_namespace}" 2>/dev/null', check=False).returncode != 0:
        run.run(f'oc new-project "{odh_namespace}" --skip-config-write >/dev/null')
    else:
        logging.warning(f"Project {odh_namespace} already exists.")
        (env.ARTIFACT_DIR / "ODH_PROJECT_ALREADY_EXISTS").touch()

    for operator in config.ci_artifacts.get_config("odh.operators"):
        run.run(f"./run_toolbox.py cluster deploy_operator {operator['catalog']} {operator['name']} {operator['namespace']}")

    for resource in config.ci_artifacts.get_config("odh.kfdefs"):
        if not resource.startswith("http"):
            run.run(f"oc apply -f {resource} -n {odh_namespace}")
            continue

        filename = "kfdef__" + pathlib.Path(resource).name

        run.run(f"curl -Ssf {resource} | tee '{env.ARTIFACT_DIR / filename}' | oc apply -f- -n {odh_namespace}")


def prepare_mcad():
    """
    Prepares the cluster and the namespace for running the MCAD tests
    """
    prepare_odh()

    prepare_mcad_test()

    run.run("./run_toolbox.py from_config rhods wait_odh")

    prepare_odh_customization()

    if config.ci_artifacts.get_config("tests.want_gpu"):
        prepare_gpu_operator()

    prepare_worker_node_labels()

    if config.ci_artifacts.get_config("tests.want_gpu"):
        run.run("./run_toolbox.py from_config gpu_operator run_gpu_burn")

    if config.ci_artifacts.get_config("clusters.sutest.worker.fill_resources.enabled"):
        namespace = config.ci_artifacts.get_config("clusters.sutest.worker.fill_resources.namespace")
        if run.run(f'oc get project "{namespace}" 2>/dev/null', check=False).returncode != 0:
            run.run(f'oc new-project "{namespace}" --skip-config-write >/dev/null')

        run.run("./run_toolbox.py from_config cluster fill_workernodes")


def prepare_ci():
    """
    Prepares the cluster and the namespace for running the MCAD tests
    """

    prepare_mcad()


def cleanup_cluster():
    """
    Restores the cluster to its original state
    """

    odh_namespace = config.ci_artifacts.get_config("odh.namespace")

    has_kfdef = run.run("oc get kfdef -n not-a-namespace --ignore-not-found", check=False).returncode == 0
    if has_kfdef:
        for resource in config.ci_artifacts.get_config("odh.kfdefs"):
            run.run(f"oc delete -f {resource} --ignore-not-found -n {odh_namespace}")
    else:
        logging.info("Cluster doesn't know the Kfdef CRD, skipping KFDef deletion")

    for operator in config.ci_artifacts.get_config("odh.operators"):
        ns = "openshift-operators" if operator['namespace'] == "all" else operator['namespace']
        run.run(f"oc delete sub {operator['name']} -n {ns} --ignore-not-found ")
        run.run(f"oc delete csv -loperators.coreos.com/{operator['name']}.{ns}= -n {ns} --ignore-not-found ")

    fill_namespace = config.ci_artifacts.get_config("clusters.sutest.worker.fill_resources.namespace")

    run.run(f"oc delete ns {odh_namespace} {fill_namespace} --ignore-not-found")

    cleanup_mcad_test()

    if config.ci_artifacts.get_config("tests.want_gpu"):
        cleanup_gpu_operator()
