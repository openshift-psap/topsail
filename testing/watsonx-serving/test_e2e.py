#!/usr/bin/env python

import sys, os
import pathlib
import subprocess
import logging
import datetime
import time
import functools
import json
import yaml

import fire
TESTING_THIS_DIR = pathlib.Path(__file__).absolute().parent
TESTING_UTILS_DIR = TESTING_THIS_DIR.parent / "utils"
PSAP_ODS_SECRET_PATH = pathlib.Path(os.environ.get("PSAP_ODS_SECRET_PATH", "/env/PSAP_ODS_SECRET_PATH/not_set"))
sys.path.append(str(TESTING_THIS_DIR.parent))

from common import env, config, run, visualize
import prepare_scale, test_scale

# ---

def consolidate_model_namespace(consolidated_model):
    namespace_prefix = config.ci_artifacts.get_config("tests.e2e.namespace")

    model_index = consolidated_model["index"]
    return f"{namespace_prefix}-{model_index}"


def consolidate_model(index, name=None, show=True):
    if name is None:
        model_list = config.ci_artifacts.get_config("tests.e2e.models")
        if index >= len(model_list):
            raise IndexError(f"Requested model index #{index}, but only {len(model_list)} are defined. {model_list}")

        model_name = model_list[index]
    else:
        model_name = name

    return prepare_scale.consolidate_model_config(_model_name=model_name, index=index, show=show)


def consolidate_models(index=None, use_job_index=False, model_name=None):
    consolidated_models = []
    if index is not None and model_name:
        consolidated_models.append(consolidate_model(index, model_name))
    elif index is not None:
        consolidated_models.append(consolidate_model(index))
    elif use_job_index:
        index = os.environ.get("JOB_COMPLETION_INDEX", None)
        if index is None:
            raise RuntimeError("No JOB_COMPLETION_INDEX env variable available :/")

        index = int(index)
        consolidated_models.append(consolidate_model(index))
    else:
        for index in range(len(config.ci_artifacts.get_config("tests.e2e.models"))):
            consolidated_models.append(consolidate_model(index))

    config.ci_artifacts.set_config("tests.e2e.consolidated_models", consolidated_models)


def dict_to_run_toolbox_args(args_dict):
    args = []
    for k, v in args_dict.items():
        if isinstance(v, dict) or isinstance(v, list):
            val = json.dumps(v)
            arg = f"--{k}=\"{v}\""
        else:
            val = str(v).replace("'", "\'")
            arg = f"--{k}='{v}'"
        args.append(arg)
    return " ".join(args)

# ---

def test_ci():
    "Executes the full e2e test"

    try:
        deploy_models_concurrently()

        test_models_concurrently()

        test_models_sequentially(locally=False)
    finally:
        try:
            run.run("./run_toolbox.py watsonx_serving capture_operators_state",
                    capture_stdout=True)
        finally:
            run.run("./run_toolbox.py cluster capture_environment",
                    capture_stdout=True)


def deploy_models_sequentially():
    "Deploys all the configured models sequentially (one after the other) -- for local usage"

    logging.info("Deploy the models sequentially")
    consolidate_models()
    deploy_consolidated_models()


def deploy_models_concurrently():
    "Deploys all the configured models concurrently (all at the same time)"

    logging.info("Deploy the models concurrently")
    run.run(f"ARTIFACT_TOOLBOX_NAME_SUFFIX=_deploy ./run_toolbox.py from_config local_ci run_multi --suffix deploy_concurrently")


def deploy_one_model(index: int = None, use_job_index: bool = False, model_name: str = None):
    "Deploys one of the configured models, according to the index parameter or JOB_COMPLETION_INDEX"

    consolidate_models(index=index, use_job_index=use_job_index, model_name=model_name)
    deploy_consolidated_models()


def test_models_sequentially(locally=False):
    "Tests all the configured models sequentially (one after the other)"

    logging.info(f"Test the models sequentially (locally={locally})")
    if locally:
        with open(env.ARTIFACT_DIR / "settings.mode.yaml", "w") as f:
            yaml.dump(dict(mode="sequential"), f, indent=4)
        consolidate_models()
        test_consolidated_models()
    else:
        run.run(f"ARTIFACT_TOOLBOX_NAME_SUFFIX=_test_sequentially ./run_toolbox.py from_config local_ci run_multi --suffix test_sequentially")


def test_models_concurrently():
    "Tests all the configured models concurrently (all at the same time)"

    logging.info("Test the models concurrently")
    run.run(f"ARTIFACT_TOOLBOX_NAME_SUFFIX=_test_concurrently ./run_toolbox.py from_config local_ci run_multi --suffix test_concurrently")


def test_one_model(index: int = None, use_job_index: bool = False, model_name: str = None):
    "Tests one of the configured models, according to the index parameter or JOB_COMPLETION_INDEX"

    if use_job_index:
        with open(env.ARTIFACT_DIR / "settings.mode.yaml", "w") as f:
            yaml.dump(dict(mode="concurrent"), f, indent=4)

    consolidate_models(index=index, use_job_index=True, model_name=model_name)
    test_consolidated_models()

# ---

def deploy_consolidated_models():
    consolidated_models = config.ci_artifacts.get_config("tests.e2e.consolidated_models")
    model_count = len(consolidated_models)
    logging.info(f"Found {model_count} models to deploy")
    for consolidated_model in consolidated_models:
        next_count = env.next_artifact_index()
        with env.TempArtifactDir(env.ARTIFACT_DIR / f"{next_count:03d}__deploy_{consolidated_model['name']}"):
            deploy_consolidated_model(consolidated_model)


def deploy_consolidated_model(consolidated_model):
    logging.info(f"Deploying model '{consolidated_model['name']}'")

    model_name = consolidated_model["name"]
    namespace = consolidate_model_namespace(consolidated_model)

    logging.info(f"Deploying a consolidated model. Changing the test namespace to '{namespace}'")

    test_scale.prepare_user_sutest_namespace(namespace)
    test_scale.deploy_storage_configuration(namespace)

    gpu_count = consolidated_model["serving_runtime"]["resource_request"].get("nvidia.com/gpu", 0)
    if config.ci_artifacts.get_config("tests.e2e.request_one_gpu") and gpu_count != 0:
        consolidated_model["serving_runtime"]["resource_request"]["nvidia.com/gpu"] = 1

    # mandatory fields
    args_dict = dict(
        namespace=namespace,
        model_id=consolidated_model["id"],
        model_name=consolidated_model["full_name"],
        serving_runtime_name=model_name,
        serving_runtime_image=consolidated_model["serving_runtime"]["image"],
        serving_runtime_resource_request=consolidated_model["serving_runtime"]["resource_request"],

        inference_service_name=model_name,
        storage_uri=consolidated_model["inference_service"]["storage_uri"],
        sa_name=config.ci_artifacts.get_config("watsonx_serving.sa_name"),

        query_data=consolidated_model["inference_service"].get("query_data"),

        mute_serving_logs=config.ci_artifacts.get_config("watsonx_serving.model.serving_runtime.mute_logs"),
    )

    # optional fields
    try: args_dict["inference_service_min_replicas"] = consolidated_model["inference_service"]["min_replicas"]
    except KeyError: pass

    if (secret_key := consolidated_model.get("secret_key")) != None:
        import test
        secret_env_file = test.PSAP_ODS_SECRET_PATH / config.ci_artifacts.get_config("secrets.watsonx_model_secret_settings")
        if not secret_env_file.exists():
            raise FileNotFoundError("Watsonx model secret settings file does not exist :/ {secret_env_file}")

        args_dict["secret_env_file_name"] = secret_env_file
        args_dict["secret_env_file_key"] = secret_key
    else:
        logging.warning("No secret env key defined for this model")

    if (extra_env := consolidated_model["serving_runtime"].get("extra_env")):
        if not isinstance(extra_env, dict):
            raise ValueError(f"serving_runtime.extra_env must be a dict. Got a {extra_env.__class__.__name__}: '{extra_env}'")
        args_dict["env_extra_values"] = extra_env

    run.run(f"./run_toolbox.py watsonx_serving deploy_model {dict_to_run_toolbox_args(args_dict)}")


def test_consolidated_models():
    consolidated_models = config.ci_artifacts.get_config("tests.e2e.consolidated_models")
    model_count = len(consolidated_models)
    logging.info(f"Found {model_count} models to test")
    for consolidated_model in consolidated_models:
        next_count = env.next_artifact_index()
        with env.TempArtifactDir(env.ARTIFACT_DIR / f"{next_count:03d}__test_{consolidated_model['name']}"):
            with open(env.ARTIFACT_DIR / "settings.yaml", "w") as f:
                settings = dict(
                    e2e_test=True,
                    model_name=consolidated_model['name'],
                    model_id=consolidated_model['id'],
                )
                yaml.dump(settings, f, indent=4)

            with open(env.ARTIFACT_DIR / "config.yaml", "w") as f:
                yaml.dump(config.ci_artifacts.config, f, indent=4)

            exit_code = 1
            try: exit_code = test_consolidated_model(consolidated_model)
            finally:
                with open(env.ARTIFACT_DIR / "exit_code", "w") as f:
                    print(f"{exit_code}", file=f)


def test_consolidated_model(consolidated_model):
    logging.info(f"Testing model '{consolidated_model['name']}")

    model_name = consolidated_model["name"]
    namespace = consolidate_model_namespace(consolidated_model)

    args_dict = dict(
        namespace=namespace,
        inference_service_names=[model_name],
        model_id=consolidated_model["id"],
        query_data=consolidated_model["inference_service"]["query_data"],
    )

    run.run(f"./run_toolbox.py watsonx_serving validate_model {dict_to_run_toolbox_args(args_dict)}")

    if not (use_llm_load_test := config.ci_artifacts.get_config("tests.e2e.llm_load_test.enabled")):
        logging.info("tests.e2e.llm_load_test.enabled is not set, stopping the testing.")
        return

    host_url = run.run(f"oc get inferenceservice/{model_name} -n {namespace} -ojsonpath={{.status.url}}", capture_stdout=True).stdout
    host = host_url.lstrip("https://") + ":443"
    if host == ":443":
        raise RuntimeError(f"Failed to get the hostname for InferenceServince {namespace}/{model_name}")
    llm_config = config.ci_artifacts.get_config("tests.e2e.llm_load_test")

    protos_path = pathlib.Path(llm_config["protos_dir"]) / llm_config["protos_file"]
    if not protos_path.exists():
        raise RuntimeError("Protos do not exist at {protos_path}")

    args_dict = dict(
        host=host,
        duration=llm_config["duration"],
        protos_path=protos_path.absolute(),
        call=llm_config["call"],
        model_id=consolidated_model["id"],
        llm_path=llm_config["src_path"],
    )

    run.run(f"./run_toolbox.py llm_load_test run {dict_to_run_toolbox_args(args_dict)}")

    return 0

# ---

def test():
    """Runs the e2e test from end to end"""
    import test
    test.test_ci()


def prepare():
    """Prepares the e2e test from end to end"""
    import test
    test.prepare_ci()


def rebuild_driver_image(pr_number):
    """Deletes and rebuilds the Driver image required for running the e2e test"""
    import test
    test.rebuild_driver_image(pr_number)


class Entrypoint:
    """
    Commands for launching the CI tests
    """

    def __init__(self):
        self.test = test
        self.prepare = prepare
        self.deploy_models_sequentially = deploy_models_sequentially
        self.deploy_models_concurrently = deploy_models_concurrently
        self.deploy_one_model = deploy_one_model

        self.test_models_sequentially = test_models_sequentially
        self.test_models_concurrently = test_models_concurrently
        self.test_one_model = test_one_model

        self.rebuild_driver_image = rebuild_driver_image


def main():
    # Print help rather than opening a pager
    fire.core.Display = lambda lines, out: print(*lines, file=out)

    fire.Fire(Entrypoint())


if __name__ == "__main__":
    try:
        os.environ["TOPSAIL_PR_ARGS"] = "e2e_gpu"
        from test import init
        init(ignore_secret_path=False, apply_preset_from_pr_args=True)

        sys.exit(main())
    except subprocess.CalledProcessError as e:
        logging.error(f"Command '{e.cmd}' failed --> {e.returncode}")
        sys.exit(1)
    except KeyboardInterrupt:
        print() # empty line after ^C
        logging.error(f"Interrupted.")
        sys.exit(1)
