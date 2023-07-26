import logging
import pathlib

from common import env, config, run
import prepare_odh, prepare_common, prepare_gpu, prepare_user_pods


def prepare():
    """
    Prepares the cluster and the namespace for running the Codeflare-SDK user test
    """

    prepare_common.prepare_common()

    namespace = config.ci_artifacts.get_config("tests.sdk_user.namespace")
    prepare_user_pods.prepare_user_pods(namespace)

    prepare_sutest_scale_up()

    run.run("./run_toolbox.py from_config cluster preload_image --prefix sutest --suffix sdk_user")

def cleanup_cluster():
    """
    Restores the cluster to its original state
    """
    prepare_common.cleanup_cluster_common()

    prepare_base_image_container()


###

import prepare_user_pods

def prepare_sutest_scale_up():
    if config.ci_artifacts.get_config("clusters.sutest.is_metal"):
        return

    node_count = prepare_user_pods.compute_node_requirement(
        cpu = config.ci_artifacts.get_config("tests.sdk_user.ray_cluster.cpu"),
        memory = config.ci_artifacts.get_config("tests.sdk_user.ray_cluster.memory"),
        machine_type = config.ci_artifacts.get_config("clusters.sutest.compute.machineset.type"),
        user_count = config.ci_artifacts.get_config("tests.sdk_user.user_count"),
    )

    extra = {}
    extra["scale"] = node_count

    run.run(f"./run_toolbox.py from_config cluster set_scale --prefix=sutest --extra \"{extra}\"")
