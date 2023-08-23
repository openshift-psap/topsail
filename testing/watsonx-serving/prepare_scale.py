import logging
import pathlib
import os

from common import env, config, run, prepare_gpu_operator, prepare_user_pods
import prepare_watsonx_serving


def prepare():
    """
    Prepares the cluster and the namespace for running the Watsonx scale tests
    """

    prepare_watsonx_serving.prepare()

    if config.ci_artifacts.get_config("tests.want_gpu"):
        prepare_gpu.prepare_gpu_operator()

    namespace = config.ci_artifacts.get_config("base_image.namespace")
    prepare_user_pods.prepare_user_pods(namespace)
