import logging
import pathlib
import os

from common import env, config, run, sizing, prepare_gpu_operator, prepare_user_pods
import prepare_watsonx_serving

def compute_sutest_node_requirement():
    user_count = config.ci_artifacts.get_config("tests.scale.user_count")
    kwargs = dict(
        cpu = 7,
        memory = 10,
        machine_type = config.ci_artifacts.get_config("clusters.sutest.compute.machineset.type"),
        user_count = user_count,
        )

    machine_count = sizing.main(**kwargs)

    # the sutest Pods must fit in one machine.
    return min(user_count, machine_count)


def prepare():
    """
    Prepares the cluster and the namespace for running the Watsonx scale tests
    """

    prepare_watsonx_serving.prepare()

    if not config.ci_artifacts.get_config("clusters.driver.is_metal"):
        node_count = compute_sutest_node_requirement()
        config.ci_artifacts.set_config("clusters.sutest.compute.machineset.count ", node_count)

        run.run(f"./run_toolbox.py from_config cluster set_scale --prefix=sutest")

    if config.ci_artifacts.get_config("tests.want_gpu"):
        prepare_gpu.prepare_gpu_operator()

    namespace = config.ci_artifacts.get_config("base_image.namespace")
    prepare_user_pods.prepare_user_pods(namespace)
