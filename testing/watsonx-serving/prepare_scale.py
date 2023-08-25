import logging
import pathlib
import os

from common import env, config, run, prepare_gpu_operator, prepare_user_pods, prepare_gpu_operator
import prepare_watsonx_serving


def prepare():
    """
    Prepares the cluster and the namespace for running the Watsonx scale tests
    """

    prepare_watsonx_serving.prepare()
    prepare_watsonx_serving.prepare_sutest()

    if config.ci_artifacts.get_config("tests.want_gpu"):
        prepare_gpu_operator.prepare_gpu_operator()

        if config.ci_artifacts.get_config("clusters.sutest.compute.dedicated"):
            toleration_key = config.ci_artifacts.get_config("clusters.sutest.compute.machineset.taint.key")
            toleration_effect = config.ci_artifacts.get_config("clusters.sutest.compute.machineset.taint.effect")
            prepare_gpu_operator.add_toleration(toleration_effect, toleration_key)

        run.run("./run_toolbox.py gpu_operator wait_stack_deployed")

    namespace = config.ci_artifacts.get_config("base_image.namespace")
    prepare_user_pods.prepare_user_pods(namespace)
