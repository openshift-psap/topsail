import logging
import pathlib
import os

from common import env, config, run, prepare_gpu_operator, prepare_user_pods, prepare_gpu_operator
import prepare_watsonx_serving


def prepare_sutest():
    with run.Parallel("prepare_sutest_1") as parallel:
        parallel.delayed(prepare_watsonx_serving.prepare)
        parallel.delayed(prepare_watsonx_serving.scale_up_sutest)

    with run.Parallel("prepare_sutest_2") as parallel:
        parallel.delayed(prepare_watsonx_serving.preload_image)
        parallel.delayed(prepare_gpu)


def prepare_gpu():
    if not config.ci_artifacts.get_config("gpu.prepare_cluster"):
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

    with run.Parallel("prepare_scale") as parallel:
        parallel.delayed(prepare_sutest)

        namespace = config.ci_artifacts.get_config("base_image.namespace")
        user_count = config.ci_artifacts.get_config("tests.scale.namespace_count")
        parallel.delayed(prepare_user_pods.prepare_user_pods, namespace, user_count)
        parallel.delayed(prepare_user_pods.cluster_scale_up, namespace, user_count)


def cluster_scale_up():
    def prepare_sutest_scale():
        prepare_watsonx_serving.scale_up_sutest()
        prepare_watsonx_serving.preload_image()

    with run.Parallel("cluster_scale_up") as parallel:
        namespace = config.ci_artifacts.get_config("base_image.namespace")
        user_count = config.ci_artifacts.get_config("tests.scale.namespace_count")
        parallel.delayed(prepare_user_pods.cluster_scale_up, namespace, user_count)

        parallel.delayed(prepare_sutest_scale)


def cluster_scale_down():
    extra = dict(scale=1)
    with run.Parallel("cluster_scale_down") as parallel:
        parallel.delayed(run.run, f"./run_toolbox.py from_config cluster set_scale --prefix=sutest --extra \"{extra}\"")
        parallel.delayed(run.run, f"./run_toolbox.py from_config cluster set_scale --prefix=driver --extra \"{extra}\"")
