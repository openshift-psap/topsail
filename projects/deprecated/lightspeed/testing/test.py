#!/usr/bin/env python

import sys, os
import pathlib
import subprocess
import fire
import logging
logging.getLogger().setLevel(logging.INFO)
import datetime
import jsonpath_ng
import time
import functools
import yaml

from projects.core.library import env, config, run, rhods

TESTING_THIS_DIR = pathlib.Path(__file__).absolute().parent

WISDOM_SECRET_PATH = pathlib.Path(os.environ["WISDOM_SECRET_PATH"])
WISDOM_PROTOS_SECRET_PATH = pathlib.Path(os.environ["WISDOM_PROTOS_SECRET_PATH"])

PSAP_ODS_SECRET_PATH = pathlib.Path(os.environ.get("PSAP_ODS_SECRET_PATH", "/env/PSAP_ODS_SECRET_PATH/not_set"))
LIGHT_PROFILE = "light"

initialized = False
def init(ignore_secret_path=False, apply_preset_from_pr_args=True):
    global initializedf
    if initialized:
        logging.debug("Already initialized.")
        return
    initialized = True

    env.init()
    config.init(TESTING_THIS_DIR)

    if apply_preset_from_pr_args:
        config.ci_artifacts.apply_preset_from_pr_args()

    if not ignore_secret_path and not PSAP_ODS_SECRET_PATH.exists():
        raise RuntimeError("Path with the secrets (PSAP_ODS_SECRET_PATH={PSAP_ODS_SECRET_PATH}) does not exists.")

    config.ci_artifacts.detect_apply_light_profile(LIGHT_PROFILE)


def entrypoint(ignore_secret_path=False, apply_preset_from_pr_args=True):
    def decorator(fct):
        @functools.wraps(fct)
        def wrapper(*args, **kwargs):
            init(ignore_secret_path, apply_preset_from_pr_args)
            fct(*args, **kwargs)

        return wrapper
    return decorator
# ---

def install_rhods():
    token_file = PSAP_ODS_SECRET_PATH / config.ci_artifacts.get_config("secrets.brew_registry_redhat_io_token_file")
    rhods.install(token_file)

    run.run_toolbox("rhods", "wait_ods")

    # run.run_toolbox_from_config("cluster", "deploy_ldap")

def max_gpu_nodes():
    test_cases = config.ci_artifacts.get_config("tests.ansible_llm.test_cases")
    replicas_list, concurrency_list = zip(*test_cases)

    mpx_test_cases = config.ci_artifacts.get_config("tests.ansible_llm.multiplexed_test_cases")
    mpx_replicas_list, concurrency_list = zip(*mpx_test_cases)

    return max(replicas_list + mpx_replicas_list)

@entrypoint()
def prepare_ci():
    """
    Prepares the cluster for running pipelines scale tests.
    """

    install_rhods()
    run.run_toolbox("rhods", "wait_ods")
    max_replicas = max_gpu_nodes()
    run.run_toolbox("cluster", "set_scale", instance_type="g5.2xlarge", scale=max_replicas)
    run.run_toolbox("nfd_operator deploy_from_operatorhub")
    run.run_toolbox("nfd wait_labels")
    run.run_toolbox("gpu_operator deploy_from_operatorhub")
    run.run_toolbox("gpu_operator wait_deployment")

    #TODO create lightspeed namespace and annotate it


    return None

def init_config():
    config.ci_artifacts.set_config("tests.config.s3_creds_model_secret_path", str(WISDOM_SECRET_PATH / "s3-secret.yaml"))
    config.ci_artifacts.set_config("tests.config.quay_secret_path", str(WISDOM_SECRET_PATH / "quay-secret.yaml"))
    config.ci_artifacts.set_config("tests.config.protos_path", str(WISDOM_PROTOS_SECRET_PATH))

    config.ci_artifacts.set_config("tests.config.s3_creds_results_secret_path", str(WISDOM_SECRET_PATH / "credentials"))
    config.ci_artifacts.set_config("tests.config.dataset_path", str(WISDOM_SECRET_PATH / "llm-load-test-dataset.json"))


def deploy_and_warmup_model(replicas):
    config.ci_artifacts.set_config("tests.config.replicas", replicas)
    run.run_toolbox_from_config("wisdom deploy_model")

    # Warmup
    run.run_toolbox_from_config("wisdom warmup_model")

@entrypoint()
def run_ci():
    """
    Runs a CI workload.

    """
    logging.info("In loadtest_run")

    init_config()

    test_namespace=config.ci_artifacts.get_config("tests.config.test_namespace")
    tester_imagestream_name=config.ci_artifacts.get_config("tests.config.tester_imagestream_name")
    tester_image_tag=config.ci_artifacts.get_config("tests.config.tester_image_tag")

    # Purely to test:
    protos_path=config.ci_artifacts.get_config("tests.config.protos_path")
    print(f"Protos path: {protos_path}")

    args = dict(
        namespace=test_namespace,
        git_repo="https://github.com/openshift-psap/llm-load-test.git",
        git_ref="main",
        dockerfile_path="build/Containerfile",
        image_local_name=tester_imagestream_name,
        tag=tester_image_tag,
    )
    run.run_toolbox("cluster", "build_push_image", **args)

    max_replicas = max_gpu_nodes()
    run.run_toolbox("cluster", "set_scale", instance="g5.2xlarge", scale=max_replicas)

    test_cases = config.ci_artifacts.get_config("tests.ansible_llm.test_cases")
    for replicas, concurrency in test_cases:
        global dataset_path

        deploy_and_warmup_model(replicas)

        total_requests = 32 * concurrency
        config.ci_artifacts.set_config("tests.config.concurrency", concurrency)
        config.ci_artifacts.set_config("tests.config.requests", total_requests)

        logging.info(f"Running load_test with replicas: {replicas}, concurrency: {concurrency} and total_requests: {total_requests}")

        run.run_toolbox_from_config("wisdom", "run_llm_load_test")

    # Switch to multiplexed dataset
    config.ci_artifacts.set_config("tests.config.dataset_path", str(WISDOM_SECRET_PATH / "llm-load-test-multiplexed-dataset.json"))
    multiplexed_test_cases = config.ci_artifacts.get_config("tests.ansible_llm.multiplexed_test_cases")
    for replicas, concurrency in multiplexed_test_cases:

        # There will be <concurrency> num instances of ghz. However, some instances
        # requests will be much smaller and will be answered more quickly.
        # To ensure that the requests are multiplexed throughout the run,
        # we set max requests high, and rely on the timeout after 10m to end the test.
        requests_per_instance = 400
        max_duration = "10m"

        logging.info(f"Running multiplexed load_test with replicas: {replicas}, total concurrency: {concurrency} and requests_per_instance: {requests_per_instance}")

        deploy_and_warmup_model(replicas)

        # There are 8 threads running the same configuration, so the total concurrency should be divided by 8
        config.ci_artifacts.set_config("tests.config.concurrency", int(concurrency/8))
        config.ci_artifacts.set_config("tests.config.requests", requests_per_instance)
        config.ci_artifacts.set_config("tests.config.max_duration", max_duration)

        run.run_toolbox_from_config("wisdom", "run_llm_load_test_multiplexed")

    pass


class LoadTest:
    """
    Commands for launching the Pipeline Perf & Scale tests
    """

    def __init__(self):
        self.prepare_ci = prepare_ci
        self.run_ci = run_ci

def main():
    # Print help rather than opening a pager
    fire.core.Display = lambda lines, out: print(*lines, file=out)

    fire.Fire(LoadTest())


if __name__ == "__main__":
    try:
        sys.exit(main())
    except subprocess.CalledProcessError as e:
        logging.error(f"Command '{e.cmd}' failed --> {e.returncode}")
        sys.exit(1)
