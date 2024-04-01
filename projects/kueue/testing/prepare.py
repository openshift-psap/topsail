import os
import pathlib
import logging

from topsail.testing import env, config, run, rhods, visualize, configure_logging, export, prepare_gpu_operator

TESTING_THIS_DIR = pathlib.Path(__file__).absolute().parent
PSAP_ODS_SECRET_PATH = pathlib.Path(os.environ.get("PSAP_ODS_SECRET_PATH", "/env/PSAP_ODS_SECRET_PATH/not_set"))

def prepare():
    with run.Parallel("prepare1") as parallel:
        parallel.delayed(prepare_rhoai)

    with run.Parallel("prepare2") as parallel:
        parallel.delayed(prepare_gpu)
        parallel.delayed(prepare_scheduler_test)


def prepare_scheduler_test():
    namespace = config.ci_artifacts.get_config("tests.schedulers.namespace")

    if run.run(f'oc get project -oname "{namespace}" 2>/dev/null', check=False).returncode != 0:
        run.run(f'oc new-project "{namespace}" --skip-config-write >/dev/null')
    else:
        logging.warning(f"Project '{namespace}' already exists.")
        (env.ARTIFACT_DIR / "PROJECT_ALREADY_EXISTS").touch()

    run.run(f"oc apply -f {TESTING_THIS_DIR}/kueue-queue.yaml -n {namespace}")


def prepare_gpu():
    if not config.ci_artifacts.get_config("gpu.prepare_cluster"):
        return

    prepare_gpu_operator.prepare_gpu_operator()

    if config.ci_artifacts.get_config("clusters.sutest.compute.dedicated"):
        toleration_key = config.ci_artifacts.get_config("clusters.sutest.compute.machineset.taint.key")
        toleration_effect = config.ci_artifacts.get_config("clusters.sutest.compute.machineset.taint.effect")
        prepare_gpu_operator.add_toleration(toleration_effect, toleration_key)

    prepare_gpu_operator.wait_ready(enable_time_sharing=False, wait_stack_deployed=False, wait_metrics=False)


def prepare_rhoai():
    if not PSAP_ODS_SECRET_PATH.exists():
        raise RuntimeError(f"Path with the secrets (PSAP_ODS_SECRET_PATH={PSAP_ODS_SECRET_PATH}) does not exists.")

    token_file = PSAP_ODS_SECRET_PATH / config.ci_artifacts.get_config("secrets.brew_registry_redhat_io_token_file")
    rhods.install(token_file)

    has_dsc = run.run("oc get dsc -oname", capture_stdout=True).stdout
    run.run_toolbox(
        "rhods", "update_datasciencecluster",
        enable=["kueue", "codeflare"],
        name=None if has_dsc else "default-dsc",
    )


def cleanup_mcad_test():
    namespace = config.ci_artifacts.get_config("tests.schedulers.namespace")
    run.run(f"oc delete namespace '{namespace}' --ignore-not-found")


def cleanup_rhoai(mute=True):
    rhods.uninstall(mute)


def cluster_scale_down(to_zero):
    if config.ci_artifacts.get_config("clusters.sutest.is_metal"):
        return

    machineset_name = config.ci_artifacts.get_config("clusters.sutest.compute.machineset.name")
    has_machineset = run.run(f"oc get machineset {machineset_name} -n openshift-machine-api -oname --ignore-not-found", capture_stdout=True).stdout
    if not has_machineset:
        logging.info(f"No {machineset_name} machineset. Nothing to scale down.")
        return

    replicas = 0 if to_zero else 1
    run.run(f"oc scale --replicas={replicas} machineset/{machineset_name} -n openshift-machine-api")


def cleanup_sutest_ns():
    cleanup_mcad_test()


def prepare_test_nodes(name, cfg, dry_mode):
    extra = {}

    if config.ci_artifacts.get_config("clusters.sutest.is_metal"):
        return

    extra["instance_type"] = cfg["node"]["instance_type"]
    extra["scale"] = cfg["node"]["count"]

    if dry_mode:
        logging.info(f"dry_mode: scale up the cluster for the test '{name}': {extra} ")
        return

    run.run_toolbox_from_config("cluster", "set_scale", prefix="sutest", extra=extra)

    if cfg["node"].get("wait_gpus", True):
        if not config.ci_artifacts.get_config("tests.want_gpu"):
            logging.error("Cannot wait for GPUs when tests.want_gpu is disabled ...")
        else:
            run.run_toolbox("gpu_operator", "wait_stack_deployed")
