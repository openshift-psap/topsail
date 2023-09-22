#!/usr/bin/env python

import sys, os
import pathlib
import subprocess
import logging
import datetime
import time
import functools
import json

import fire
TESTING_THIS_DIR = pathlib.Path(__file__).absolute().parent
TESTING_UTILS_DIR = TESTING_THIS_DIR.parent / "utils"
PSAP_ODS_SECRET_PATH = pathlib.Path(os.environ.get("PSAP_ODS_SECRET_PATH", "/env/PSAP_ODS_SECRET_PATH/not_set"))
sys.path.append(str(TESTING_THIS_DIR.parent))

from common import env, config, run, visualize
import prepare_scale, test_scale

# ---

def consolidate_model(index):
    model_list = config.ci_artifacts.get_config("tests.e2e.models")
    if index >= len(model_list):
        raise IndexError(f"Requested model index #{index}, but only {len(model_list)} are defined. {model_list}")

    model_name = model_list[index]

    return prepare_scale.consolidate_model_config(_model_name=model_name, index=index)


def consolidate_models(index=None, use_job_index=False):
    consolidated_models = []
    if index or use_job_index:
        if index is None and use_job_index:
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

    deploy_models_concurrently()

    run.run(f"ARTIFACT_TOOLBOX_NAME_SUFFIX=_test_sequentially ./run_toolbox.py from_config local_ci run_multi --suffix test_sequentially")

    test_models_concurrently()


def deploy_models_sequentially():
    "Deploys all the configured models sequentially (one after the other) -- for local usage"

    logging.info("Deploy the models sequentially")
    consolidate_models()
    deploy_consolidated_models()


def deploy_models_concurrently():
    "Deploys all the configured models concurrently (all at the same time)"

    logging.info("Deploy the models concurrently")
    run.run(f"ARTIFACT_TOOLBOX_NAME_SUFFIX=_deploy ./run_toolbox.py from_config local_ci run_multi --suffix deploy_concurrently")


def deploy_one_model(index=None, use_job_index=False):
    "Deploys one of the configured models, according to the index parameter or JOB_COMPLETION_INDEX"

    consolidate_models(index=index, use_job_index=use_job_index)
    deploy_consolidated_models()


def test_models_sequentially():
    "Tests all the configured models sequentially (one after the other)"

    logging.info("Test the models sequentially")
    consolidate_models()
    test_consolidated_models()


def test_models_concurrently():
    "Tests all the configured models concurrently (all at the same time)"

    logging.info("Test the models concurrently")
    run.run(f"ARTIFACT_TOOLBOX_NAME_SUFFIX=_test_concurrently ./run_toolbox.py from_config local_ci run_multi --suffix test_concurrently")


def test_one_model(index=None, use_job_index=False):
    "Tests one of the configured models, according to the index parameter or JOB_COMPLETION_INDEX"

    consolidate_models(index=index, use_job_index=True)
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

    namespace_prefix = config.ci_artifacts.get_config("tests.e2e.namespace")
    model_name = consolidated_model["name"]
    model_index = consolidated_model["index"]
    namespace = f"{namespace_prefix}-{model_index}-{model_name}"

    logging.info(f"Deploying a consolidated model. Changing the test namespace to '{namespace}'")

    test_scale.prepare_user_sutest_namespace(namespace)
    test_scale.deploy_storage_configuration(namespace)

    # mandatory fields
    args_dict = dict(
        namespace=namespace,
        model_name=consolidated_model["full_name"],
        serving_runtime_name=model_name,
        serving_runtime_image=consolidated_model["serving_runtime"]["image"],
        serving_runtime_resource_request=consolidated_model["serving_runtime"]["resource_request"],

        inference_service_name=model_name,
        storage_uri=consolidated_model["inference_service"]["storage_uri"],
        sa_name=config.ci_artifacts.get_config("watsonx_serving.sa_name"),
    )

    # optional fields
    try: args_dict["min_replicas"] = consolidated_model["inference_service"]["min_replicas"]
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

    if (runtime_config := consolidated_model["serving_runtime"].get("runtime_config")) == True:
        args_dict["runtime_config_file"] = TESTING_THIS_DIR / "models" / "resources" / "runtime_config.yaml"
        if not args_dict["runtime_config_file"].exists():
            raise FileNotFoundError(f"Unexpected error: {args_dict['runtime_config_file']} does not exist :/")

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
            test_consolidated_model(consolidated_model)


def test_consolidated_model(consolidated_model):
    logging.info(f"Testing model '{consolidated_model['name']}")

    namespace_prefix = config.ci_artifacts.get_config("tests.e2e.namespace")
    model_name = consolidated_model["name"]
    model_index = consolidated_model["index"]
    namespace = f"{namespace_prefix}-{model_index}-{model_name}"

    args_dict = dict(
        namespace=namespace,
        inference_service_names=[model_name],
        model_id=consolidated_model["id"],
        query_data=consolidated_model["inference_service"]["query_data"],
    )

    run.run(f"./run_toolbox.py watsonx_serving validate_model {dict_to_run_toolbox_args(args_dict)}")

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
        os.environ["TOPSAIL_PR_ARGS"] = "e2e"
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
