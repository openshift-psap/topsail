import os
import pathlib

from topsail.testing import env, config, run, rhods, visualize, configure_logging, export

PSAP_ODS_SECRET_PATH = pathlib.Path(os.environ.get("PSAP_ODS_SECRET_PATH", "/env/PSAP_ODS_SECRET_PATH/not_set"))

def prepare():
    with run.Parallel("prepare1") as parallel:
        parallel.delayed(prepare_rhoai)
        parallel.delayed(cluster_scale_up)

    with run.Parallel("prepare2") as parallel:
        parallel.delayed(prepare_gpu)


def prepare_gpu():
    if not config.ci_artifacts.get_config("gpu.prepare_cluster"):
        return

    prepare_gpu_operator.prepare_gpu_operator()

    if config.ci_artifacts.get_config("clusters.sutest.compute.dedicated"):
        toleration_key = config.ci_artifacts.get_config("clusters.sutest.compute.machineset.taint.key")
        toleration_effect = config.ci_artifacts.get_config("clusters.sutest.compute.machineset.taint.effect")
        prepare_gpu_operator.add_toleration(toleration_effect, toleration_key)

    prepare_gpu_operator.wait_ready()


def prepare_rhoai():
    if not PSAP_ODS_SECRET_PATH.exists():
        raise RuntimeError(f"Path with the secrets (PSAP_ODS_SECRET_PATH={PSAP_ODS_SECRET_PATH}) does not exists.")

    token_file = PSAP_ODS_SECRET_PATH / config.ci_artifacts.get_config("secrets.brew_registry_redhat_io_token_file")
    rhods.install(token_file)

    has_dsc = run.run("oc get dsc -oname", capture_stdout=True).stdout
    run.run_toolbox(
        "rhods", "update_datasciencecluster",
        enable=["kueue"],
        name=None if has_dsc else "default-dsc",
    )

def cleanup_rhoai(mute=True):
    rhods.uninstall(mute)


def cluster_scale_up():
    scale_up_sutest()


def kueue_compute_sutest_node_requirement():
    return 1


def scale_up_sutest():
    if config.ci_artifacts.get_config("clusters.sutest.is_metal"):
        return

    test_mode = config.ci_artifacts.get_config("tests.mode")
    node_count = config.ci_artifacts.get_config("clusters.sutest.compute.machineset.count")
    if node_count is not None:
        logging.info(f"Using the sutest node count from the configuration: {node_count}")
    elif test_mode in ("kueue"):
        node_count = kueue_compute_sutest_node_requirement()
    else:
        raise KeyError(f"Invalid test mode: {test_mode}")

    extra = dict(scale=node_count)
    run.run_toolbox_from_config("cluster", "set_scale", prefix="sutest", extra=extra, artifact_dir_suffix="_sutest")


def cluster_scale_down(to_zero):
    if config.ci_artifacts.get_config("clusters.sutest.is_metal"):
        return

    extra = dict(scale=0 if to_zero else 1)
    with run.Parallel("cluster_scale_down") as parallel:
        parallel.delayed(run.run_toolbox_from_config, "cluster", "set_scale", prefix="sutest", extra=extra)
        parallel.delayed(run.run_toolbox_from_config, "cluster", "set_scale", prefix="driver", extra=extra)


def cleanup_sutest_ns():
    #label = config.ci_artifacts.get_config("...")
    #run.run(f"oc delete ns -l{label}")
    pass

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
