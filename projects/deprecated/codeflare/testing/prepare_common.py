import logging
import pathlib

from projects.core.library import env, config, run
import prepare_odh, prepare_gpu

def prepare_common():
    deploy_from = "odh"

    test_mode = config.ci_artifacts.get_config("tests.mode")
    if test_mode == "mcad":
        deploy_from = config.ci_artifacts.get_config("codeflare.mcad.deploy_from")

    if deploy_from == "odh":
        prepare_odh.prepare_odh()
        prepare_odh.prepare_odh_customization()

    elif deploy_from == "helm":
        run.run_toolbox_from_config("codeflare", "deploy_mcad_from_helm")

    if config.ci_artifacts.get_config("tests.want_gpu"):
        prepare_gpu.prepare_gpu_operator()

    prepare_worker_node_labels()

    if config.ci_artifacts.get_config("tests.want_gpu"):
        run.run_toolbox_from_config("gpu_operator", "run_gpu_burn")

    if config.ci_artifacts.get_config("clusters.sutest.worker.fill_resources.enabled"):
        prepare_fill_workernodes()


def prepare_worker_node_labels():
    worker_label = config.ci_artifacts.get_config("clusters.sutest.worker.label")
    if run.run(f"oc get nodes -oname -l{worker_label}", capture_stdout=True).stdout:
        logging.info(f"Cluster already has {worker_label} nodes. Not applying the labels.")
    else:
        run.run(f"oc label nodes -lnode-role.kubernetes.io/worker {worker_label}")


def prepare_fill_workernodes():
    namespace = config.ci_artifacts.get_config("clusters.sutest.worker.fill_resources.namespace")
    if run.run(f'oc get project -oname "{namespace}" 2>/dev/null', check=False).returncode != 0:
        run.run(f'oc new-project "{namespace}" --skip-config-write >/dev/null')

    run.run_toolbox_from_config("cluster", "fill_workernodes")


def cleanup_fill_workernodes():
    fill_namespace = config.ci_artifacts.get_config("clusters.sutest.worker.fill_resources.namespace")

    run.run(f"oc delete ns {odh_namespace} {fill_namespace} --ignore-not-found")


def cleanup_cluster_common():
    prepare_odh.cleanup_odh()

    cleanup_fill_workernodes()

    prepare_gpu.cleanup_gpu_operator()
