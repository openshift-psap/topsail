import logging
import pathlib

from topsail.testing import env, config, run
import prepare_odh, prepare_common, prepare_gpu


def prepare_mcad_test():
    namespace = config.ci_artifacts.get_config("tests.mcad.namespace")
    if run.run(f'oc get project -oname "{namespace}" 2>/dev/null', check=False).returncode != 0:
        run.run(f'oc new-project "{namespace}" --skip-config-write >/dev/null')
    else:
        logging.warning(f"Project '{namespace}' already exists.")
        (env.ARTIFACT_DIR / "MCAD_PROJECT_ALREADY_EXISTS").touch()


def cleanup_mcad_test():
    namespace = config.ci_artifacts.get_config("tests.mcad.namespace")
    run.run(f"oc delete namespace '{namespace}' --ignore-not-found")


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


def prepare():
    """
    Prepares the cluster and the namespace for running the MCAD tests
    """

    prepare_mcad_test()
    prepare_common.prepare_common()


def cleanup_cluster():
    """
    Restores the cluster to its original state
    """

    prepare_common.cleanup_cluster_common()

    cleanup_mcad_test()
