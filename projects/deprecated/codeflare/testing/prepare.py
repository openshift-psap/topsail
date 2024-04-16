import logging
import pathlib

from projects.core.library import env, config, run

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
    run.run_toolbox("nfd_operator", "deploy_from_operatorhub")
    run.run_toolbox("gpu_operator", "deploy_from_operatorhub")
    run.run_toolbox_from_config("gpu_operator", "enable_time_sharing")


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

    run.run_toolbox_from_config("cluster", "set_scale", extra=extra)

    if cfg["node"].get("wait_gpus", True):
        if not config.ci_artifacts.get_config("tests.want_gpu"):
            logging.error("Cannot wait for GPUs when tests.want_gpu is disabled ...")
        else:
            run.run_toolbox("gpu_operator", "wait_stack_deployed")


def prepare_odh():
    odh_namespace = config.ci_artifacts.get_config("odh.namespace")
    if run.run(f'oc get project -oname "{odh_namespace}" 2>/dev/null', check=False).returncode != 0:
        run.run(f'oc new-project "{odh_namespace}" --skip-config-write >/dev/null')
    else:
        logging.warning(f"Project {odh_namespace} already exists.")
        (env.ARTIFACT_DIR / "ODH_PROJECT_ALREADY_EXISTS").touch()

    for operator in config.ci_artifacts.get_config("odh.operators"):
        run.run_toolbox("cluster", "deploy_operator", catalog=operator['catalog'], manifest_name=operator['name'], namespace=operator['namespace'], artifact_dir_suffix=operator['catalog'])

    for resource in config.ci_artifacts.get_config("odh.kfdefs"):
        if not resource.startswith("http"):
            run.run(f"oc apply -f {resource} -n {odh_namespace}")
            continue

        filename = "kfdef__" + pathlib.Path(resource).name

        run.run(f"curl -Ssf {resource} | tee '{env.ARTIFACT_DIR / filename}' | oc apply -f- -n {odh_namespace}")


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
