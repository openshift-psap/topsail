import logging
import pathlib
import os

from common import env, config, run, prepare_gpu_operator, prepare_user_pods, prepare_gpu_operator
import prepare_watsonx_serving


def prepare_sutest():
    with run.Parallel() as parallel:
        parallel.delayed(prepare_watsonx_serving.prepare)
        parallel.delayed(prepare_watsonx_serving.scale_up_sutest)

    with run.Parallel() as parallel:
        parallel.delayed(prepare_watsonx_serving.preload_image)
        parallel.delayed(prepare_gpu)


def prepare_gpu():
    if not config.ci_artifacts.get_config("tests.want_gpu"):
        return

    prepare_gpu_operator.prepare_gpu_operator()

    if config.ci_artifacts.get_config("clusters.sutest.compute.dedicated"):
        toleration_key = config.ci_artifacts.get_config("clusters.sutest.compute.machineset.taint.key")
        toleration_effect = config.ci_artifacts.get_config("clusters.sutest.compute.machineset.taint.effect")
        prepare_gpu_operator.add_toleration(toleration_effect, toleration_key)

    run.run("./run_toolbox.py gpu_operator wait_stack_deployed")


def prepare():
    """
    Prepares the cluster and the namespace for running the Watsonx scale tests
    """

    with run.Parallel() as parallel:
        parallel.delayed(prepare_sutest)

        namespace = config.ci_artifacts.get_config("base_image.namespace")
        parallel.delayed(prepare_user_pods.prepare_user_pods, namespace)
