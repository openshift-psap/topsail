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

    node_count = prepare_user_pods.compute_node_requirement(sutest=True)

    extra = {}
    extra["scale"] = node_count

    run.run(f"./run_toolbox.py from_config cluster set_scale --prefix=sutest --extra \"{extra}\"")
