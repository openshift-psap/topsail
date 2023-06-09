#!/usr/bin/env python3

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

TESTING_ANSIBLE_LLM_DIR = pathlib.Path(__file__).absolute().parent
WISDOM_SECRET_PATH = pathlib.Path(os.environ["WISDOM_SECRET_PATH"])
WISDOM_PROTOS_SECRET_PATH = pathlib.Path(os.environ["WISDOM_PROTOS_SECRET_PATH"])
PSAP_ODS_SECRET_PATH = pathlib.Path(os.environ.get("PSAP_ODS_SECRET_PATH", "/env/PSAP_ODS_SECRET_PATH/not_set"))
LIGHT_PROFILE = "light"

sys.path.append(str(TESTING_ANSIBLE_LLM_DIR.parent))
from common import env, config, run, rhods, visualize

initialized = False
def init(ignore_secret_path=False):
    global initialized
    if initialized:
        logging.info("Already initialized.")
        return
    initialized = True

    env.init()
    config.init(TESTING_ANSIBLE_LLM_DIR)

    if not ignore_secret_path and not PSAP_ODS_SECRET_PATH.exists():
        raise RuntimeError("Path with the secrets (PSAP_ODS_SECRET_PATH={PSAP_ODS_SECRET_PATH}) does not exists.")

    if os.environ.get("JOB_NAME_SAFE", "").endswith("-light"):
        logging.info(f"Running a light test, applying the '{LIGHT_PROFILE}' profile")
        config.ci_artifacts.apply_preset(LIGHT_PROFILE)


def entrypoint(ignore_secret_path=False):
    def decorator(fct):
        @functools.wraps(fct)
        def wrapper(*args, **kwargs):
            init(ignore_secret_path)
            fct(*args, **kwargs)

        return wrapper
    return decorator
# ---

def install_rhods():
    try:
        run.run("oc get csv -n redhat-ods-operator -oname | grep rhods-operator --quiet")
        logging.warning("RHODS is already installed, do not reinstall it.")
        return
    except Exception: pass # RHODS isn't installed, proceed

    run.run("./run_toolbox.py cluster deploy_operator redhat-operators rhods-operator redhat-ods-operator --all_namespaces")

def max_gpu_nodes():
    test_cases = config.ci_artifacts.get_config("tests.ansible_llm.test_cases")
    replicas_list, concurrency_list = zip(*test_cases)

    return max(replicas_list)

@entrypoint()
def load_test_prepare():
    """
    Prepares the cluster for running pipelines scale tests.
    """
    install_rhods()
    run.run("./run_toolbox.py rhods wait_ods")
    max_replicas = max_gpu_nodes()
    run.run(f"./run_toolbox.py cluster set_scale g5.2xlarge {max_replicas}")
    run.run("./run_toolbox.py nfd_operator deploy_from_operatorhub")
    run.run("./run_toolbox.py nfd wait_labels")
    run.run("./run_toolbox.py gpu_operator deploy_from_operatorhub")
    run.run("./run_toolbox.py gpu_operator wait_deployment")

    #TODO create lightspeed namespace and annotate it


    return None

@entrypoint()
def load_test_run():
    """
    Runs a CI workload.

    """
    logging.info("In loadtest_run")
    protos_path = WISDOM_PROTOS_SECRET_PATH
    s3_creds_model_secret_path = WISDOM_SECRET_PATH / "s3-secret.yaml"
    quay_secret_path = WISDOM_SECRET_PATH / "quay-secret.yaml"
    dataset_path = WISDOM_SECRET_PATH / "llm-load-test-dataset.json"
    s3_creds_results_secret_path = WISDOM_SECRET_PATH / "credentials"

    test_namespace="wisdom"
    tester_imagestream_name="llm-load-test"
    tester_image_tag="wisdom-ci"

    run.run(f"./run_toolbox.py utils build_push_image --namespace='{test_namespace}'  --git_repo='https://github.com/openshift-psap/llm-load-test.git' --git_ref='main' --dockerfile_path='build/Containerfile' --image_local_name='{tester_imagestream_name}' --tag='{tester_image_tag}'  --")

    max_replicas = max_gpu_nodes()
    run.run(f"./run_toolbox.py cluster set_scale g5.2xlarge {max_replicas}")

    test_cases = config.ci_artifacts.get_config("tests.ansible_llm.test_cases")

    #TODO: These test cases should be in a config.yaml, not hardcoded
    for replicas, concurrency in test_cases:

        total_requests = 32 * concurrency

        logging.info(f"Configure ServingRuntime and InferenceService for replicas: {replicas}")

        #TODO: USE TEST IMAGE BUILT IN PREPARE STEP
        run.run(f"./run_toolbox.py wisdom deploy_model {replicas} \
            {s3_creds_model_secret_path} \
            {quay_secret_path} \
            {protos_path} \
            {tester_imagestream_name} \
            {tester_image_tag} \
            --namespace='{test_namespace}' \
            --")

        # Warmup
        run.run(f"./run_toolbox.py wisdom warmup_model {protos_path} \
            {tester_imagestream_name} \
            {tester_image_tag} \
            --namespace='{test_namespace}'")

        #Run test with total_requests and concurrency
        logging.info(f"Running load_test with replicas: {replicas}, concurrency: {concurrency} and total_requests: {total_requests}")
        run.run(f"./run_toolbox.py wisdom run_llm_load_test {total_requests} \
            {concurrency} \
            {replicas} \
            {dataset_path} \
            {s3_creds_results_secret_path} \
            {protos_path} \
            {tester_imagestream_name} \
            {tester_image_tag} \
            --namespace='{test_namespace}'")


    pass


class LoadTest:
    """
    Commands for launching the Pipeline Perf & Scale tests
    """

    def __init__(self):
        self.prepare = load_test_prepare
        self.run = load_test_run

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
