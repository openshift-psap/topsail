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
import yaml

def run(command):
    logging.info(f"run: {command}")
    return subprocess.run(command, check=True, shell=True)

TESTING_ANSIBLE_LLM_DIR = pathlib.Path(__file__).absolute().parent
WISDOM_SECRET_PATH = pathlib.Path(os.environ["WISDOM_SECRET_PATH"])
WISDOM_PROTOS_SECRET_PATH = pathlib.Path(os.environ["WISDOM_PROTOS_SECRET_PATH"])

try:
    ARTIFACT_DIR = pathlib.Path(os.environ["ARTIFACT_DIR"])
except KeyError:
    env_ci_artifact_base_dir = pathlib.Path(os.environ.get("CI_ARTIFACT_BASE_DIR", "/tmp"))
    ARTIFACT_DIR = env_ci_artifact_base_dir / f"ci-artifacts_{time.strftime('%Y%m%d')}"
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

os.environ["CI_ARTIFACTS_FROM_CONFIG_FILE"] = str(TESTING_ANSIBLE_LLM_DIR / "config.yaml")

with open(os.environ["CI_ARTIFACTS_FROM_CONFIG_FILE"]) as config_f:
    config = yaml.safe_load(config_f)

# TODO
def get_config(jsonpath):
    try:
        value = jsonpath_ng.parse(jsonpath).find(config)[0].value
    except Exception as ex:
        logging.error(f"get_config: {jsonpath} --> {ex}")
        raise ex

    logging.info(f"get_config: {jsonpath} --> {value}")

    return value

def install_rhods():

    try:
        run("oc get csv -n redhat-ods-operator -oname | grep rhods-operator --quiet")
        logging.warning("RHODS is already installed, do not reinstall it.")
        return
    except Exception: pass # RHODS isn't installed, proceed

    run("./run_toolbox.py cluster deploy_operator redhat-operators rhods-operator redhat-ods-operator --all_namespaces")


def load_test_prepare():
    """
    Prepares the cluster for running pipelines scale tests.
    """

    install_rhods()
    run("./run_toolbox.py rhods wait_ods")
    run("./run_toolbox.py cluster set_scale g5.2xlarge 2")    
    run("./run_toolbox.py nfd_operator deploy_from_operatorhub")
    run("./run_toolbox.py nfd wait_labels")
    run("./run_toolbox.py gpu_operator deploy_from_operatorhub")
    run("./run_toolbox.py gpu_operator wait_deployment")

    #TODO create lightspeed namespace and annotate it


    return None


def loadtest_run():
    """
    Runs a CI workload.

    """
    print("In loadtest_run")
    protos_path = WISDOM_PROTOS_SECRET_PATH
    s3_creds_model_secret_path = WISDOM_SECRET_PATH / "s3-secret.yaml"
    quay_secret_path = WISDOM_SECRET_PATH / "quay-secret.yaml"
    dataset_path = WISDOM_SECRET_PATH / "llm-load-test-dataset.json"
    s3_creds_results_secret_path = WISDOM_SECRET_PATH / "credentials"

    test_namespace="wisdom"
    tester_imagestream_name="llm-load-test"
    tester_image_tag="wisdom-ci"

    run(f"./run_toolbox.py utils build_push_image --namespace='{test_namespace}'  --git_repo='https://github.com/openshift-psap/llm-load-test.git' --git_ref='main' --dockerfile_path='build/Containerfile' --image_local_name='{tester_imagestream_name}' --tag='{tester_image_tag}'  --")

    test_cases = get_config("tests.ansible_llm.test_cases")
    replicas_list, concurrency_list = zip(*test_cases)
    
    # It takes > 5 minutes for a new GPU Node to become ready for GPU Pods, so
    # scaleup once at the beginning.
    max_replicas = max(replicas_list)  
    run(f"./run_toolbox.py cluster set_scale g5.2xlarge {max_replicas}")
 
    #TODO: These test cases should be in a config.yaml, not hardcoded
    for replicas, concurrency in test_cases:

        total_requests = 32 * concurrency

        print(f"Configure ServingRuntime and InferenceService for replicas: {replicas}")

        #TODO: USE TEST IMAGE BUILT IN PREPARE STEP
        run(f"./run_toolbox.py wisdom deploy_model {replicas} \
            {s3_creds_model_secret_path} \
            {quay_secret_path} \
            {protos_path} \
            {tester_imagestream_name} \
            {tester_image_tag} \
            --namespace='{test_namespace}' \
            --")

        # Warmup 
        run(f"./run_toolbox.py wisdom warmup_model {protos_path} \
            {tester_imagestream_name} \
            {tester_image_tag} \
            --namespace='{test_namespace}'")
        
        #Run test with total_requests and concurrency
        print(f"Running load_test with replicas: {replicas}, concurrency: {concurrency} and total_requests: {total_requests}")
        run(f"./run_toolbox.py wisdom run_llm_load_test {total_requests} \
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
        self.run = loadtest_run
        
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
