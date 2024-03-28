import os
import pathlib

from topsail.testing import env, config, run, rhods, visualize, configure_logging, export

PSAP_ODS_SECRET_PATH = pathlib.Path(os.environ.get("PSAP_ODS_SECRET_PATH", "/env/PSAP_ODS_SECRET_PATH/not_set"))

def prepare():
    prepare_rhoai()


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
