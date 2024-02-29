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
import uuid

import fire

PSAP_ODS_SECRET_PATH = pathlib.Path(os.environ.get("PSAP_ODS_SECRET_PATH", "/env/PSAP_ODS_SECRET_PATH/not_set"))

import topsail
from topsail.testing import env, config, run, visualize, matbenchmark
import prepare_scale, test_scale, prepare_kserve

TOPSAIL_DIR = pathlib.Path(topsail.__file__).parent.parent
RUN_DIR = pathlib.Path(os.getcwd()) # for run_one_matbench
os.chdir(TOPSAIL_DIR)

# ---

def consolidate_model_namespace(consolidated_model):
    namespace_prefix = config.ci_artifacts.get_config("tests.e2e.namespace")

    model_index = consolidated_model["index"]
    return f"{namespace_prefix}-{model_index}"


def consolidate_model(index=None, name=None, show=True):
    if name is None:
        model_list = config.ci_artifacts.get_config("tests.e2e.models")
        if index >= len(model_list):
            raise IndexError(f"Requested model index #{index}, but only {len(model_list)} are defined. {model_list}")

        model_name = model_list[index]
    else:
        model_name = name

    return prepare_scale.consolidate_model_config(_model_name=model_name, index=index, show=show)


def consolidate_models(index=None, use_job_index=False, model_name=None, namespace=None, save=True):
    consolidated_models = []
    if model_name and namespace:
        consolidated_models.append(consolidate_model(name=model_name))
    elif index is not None and model_name:
        consolidated_models.append(consolidate_model(index=index, name=model_name))
    elif index is not None:
        consolidated_models.append(consolidate_model(index=index))
    elif use_job_index:
        index = os.environ.get("JOB_COMPLETION_INDEX", None)
        if index is None:
            raise RuntimeError("No JOB_COMPLETION_INDEX env variable available :/")

        index = int(index)
        consolidated_models.append(consolidate_model(index=index))
    else:
        for index in range(len(config.ci_artifacts.get_config("tests.e2e.models"))):
            consolidated_models.append(consolidate_model(index=index))

    if namespace is not None:
        for consolidated_model in consolidated_models:
            consolidated_model["namespace"] = namespace

    config.ci_artifacts.set_config("tests.e2e.consolidated_models", consolidated_models)

    if save:
        dump = yaml.dump(consolidated_models,  default_flow_style=False, sort_keys=False).strip()

        with open(env.ARTIFACT_DIR / "consolidated_models.yaml", "w") as f:
            print(dump, file=f)

    return consolidated_models

# ---

def test_ci():
    "Executes the full e2e test"

    # in the OCP CI, the config is passed from 'prepare' to 'test', so this is a NOOP
    # in the Perf CI environment, the config isn't passed, so this is mandatory.
    prepare_kserve.update_serving_runtime_images()
    mode = config.ci_artifacts.get_config("tests.e2e.mode")
    try:
        if mode == "single":
            single_model_deploy_and_test_sequentially(locally=False)
        elif mode == "longevity":
            test_models_longevity()
        else:
            multi_model_deploy_and_test()

    finally:
        exc = None
        if config.ci_artifacts.get_config("tests.e2e.capture_state"):
            raw_deployment = config.ci_artifacts.get_config("kserve.raw_deployment.enabled")

            exc = run.run_and_catch(
                exc,
                run.run_toolbox, "kserve", "capture_operators_state", raw_deployment=raw_deployment,
                run_kwargs=dict(capture_stdout=True),
            )

            exc = run.run_and_catch(
                exc,
                run.run_toolbox, "cluster", "capture_environment", run_kwargs=dict(capture_stdout=True),
            )

            if exc: raise exc


def deploy_models_sequentially():
    "Deploys all the configured models sequentially (one after the other) -- for local usage"

    logging.info("Deploy the models sequentially")
    consolidate_models()
    deploy_consolidated_models()


def deploy_models_concurrently():
    "Deploys all the configured models concurrently (all at the same time)"

    logging.info("Deploy the models concurrently")
    run.run_toolbox_from_config("local_ci", "run_multi", suffix="deploy_concurrently", artifact_dir_suffix="_deploy")


def deploy_one_model(index: int = None, use_job_index: bool = False, model_name: str = None):
    "Deploys one of the configured models, according to the index parameter or JOB_COMPLETION_INDEX"

    consolidate_models(index=index, use_job_index=use_job_index, model_name=model_name)
    deploy_consolidated_models()


def multi_model_test_sequentially(locally=False):
    "Tests all the configured models sequentially (one after the other)"

    logging.info(f"Test the models sequentially (locally={locally})")
    if locally:
        with open(env.ARTIFACT_DIR / "settings.mode.yaml", "w") as f:
            yaml.dump(dict(mode="sequential"), f, indent=4)
        consolidate_models()
        test_consolidated_models()
        return

    # launch the remote execution

    reset_prometheus()
    try:
        run.run_toolbox_from_config("local_ci", "run_multi", suffix="test_sequentially",
                                    artifact_dir_suffix="_test_sequentially")
    finally:
        generate_kserve_prom_results("multi-model_sequential")


def test_models_longevity():
    repeat = config.ci_artifacts.get_config("tests.e2e.longevity.repeat")
    delay = config.ci_artifacts.get_config("tests.e2e.longevity.delay")

    multi_model_deploy_concurrently()

    for i in range(repeat):
        expe_name = f"longevity_{i}"
        with env.NextArtifactDir(expe_name):

            with open(env.ARTIFACT_DIR / "settings.longevity.yaml", "w") as f:
                yaml.dump(dict(longevity_index=i), f, indent=4)

            multi_model_test_concurrently(expe_name)

            if i != repeat-1:
                time.sleep(delay)


def multi_model_deploy_and_test():

    multi_model_deploy_concurrently()

    multi_model_test_concurrently()
    multi_model_test_sequentially(locally=False)


def single_model_deploy_and_test_sequentially(locally=False):
    "Deploy and test all the configured models sequentially (one after the other)"

    logging.info(f"Deploy and test the models sequentially (locally={locally})")
    if not locally:
        return run.run_toolbox_from_config("local_ci", "run_multi", suffix="deploy_and_test_sequentially", artifact_dir_suffix="_e2e_perf_test")


    with open(env.ARTIFACT_DIR / "settings.mode.yaml", "w") as f:
        yaml.dump(dict(mode="alone"), f, indent=4)

    namespace = config.ci_artifacts.get_config("tests.e2e.namespace") + "-perf"
    consolidated_models = consolidate_models(namespace=namespace)

    run.run_toolbox("kserve", "undeploy_model", namespace=namespace, all=True)

    exc = None
    failed = []
    for consolidated_model in consolidated_models:
        with env.NextArtifactDir(consolidated_model['name']):
            try:
                reset_prometheus()

                deploy_consolidated_model(consolidated_model)

                launch_test_consolidated_model(consolidated_model, dedicated_dir=False)
            except Exception as e:
                failed += [consolidated_model['name']]
                with open(env.ARTIFACT_DIR / "FAILURE", "a") as f:
                    print(f"{consolidated_model['name']} failed: {e.__class__.__name__}: {e}", file=f)
                exc = e

            generate_kserve_prom_results("single_model")

            run.run_and_catch(exc, undeploy_consolidated_model, consolidated_model)

    if failed:
        logging.fatal(f"single_model_deploy_and_test_sequentially: {len(failed)} tests failed :/ {' '.join(failed)}")
        raise exc


def multi_model_test_concurrently(expe_name="multi-model_concurrent"):
    "Tests all the configured models concurrently (all at the same time)"

    reset_prometheus()

    try:
        logging.info(f"Test the models concurrently ({expe_name})")
        run.run_toolbox_from_config("local_ci", "run_multi", suffix="test_concurrently", artifact_dir_suffix="_test_concurrently")
    finally:
        generate_kserve_prom_results(expe_name)


def test_one_model(index: int = None, use_job_index: bool = False, model_name: str = None, namespace: str = None):
    "Tests one of the configured models, according to the index parameter or JOB_COMPLETION_INDEX"

    if use_job_index:
        with open(env.ARTIFACT_DIR / "settings.mode.yaml", "w") as f:
            yaml.dump(dict(mode="concurrent"), f, indent=4)

    consolidate_models(index=index, use_job_index=True, model_name=model_name, namespace=namespace)
    test_consolidated_models()

# ---

def reset_prometheus(delay=60):
    if not config.ci_artifacts.get_config("tests.capture_prom"):
        logging.info("tests.capture_prom is disabled, skipping Prometheus DB reset")
        return

    with run.Parallel("cluster__reset_prometheus_dbs") as parallel:
        parallel.delayed(run.run_toolbox, "cluster", "reset_prometheus_db", mute_stdout=True)
        parallel.delayed(run.run_toolbox_from_config, "cluster", "reset_prometheus_db", suffix="uwm", artifact_dir_suffix="_uwm", mute_stdout=True)

    logging.info(f"Wait {delay}s for Prometheus to restart collecting data ...")
    time.sleep(delay)


def dump_prometheus(delay=60):
    if not config.ci_artifacts.get_config("tests.capture_prom"):
        logging.info("tests.capture_prom is disabled, skipping Prometheus DB dump")
        return

    logging.info(f"Wait {delay}s for Prometheus to finish collecting data ...")
    time.sleep(delay)

    with run.Parallel("cluster__dump_prometheus_dbs") as parallel:
        parallel.delayed(run.run_toolbox, "cluster", "dump_prometheus_db", mute_stdout=True)
        parallel.delayed(run.run_toolbox_from_config, "cluster", "dump_prometheus_db", suffix="uwm", artifact_dir_suffix="_uwm", mute_stdout=True)


def generate_kserve_prom_results(expe_name):
    # flag file for kserve-prom visualization
    with open(env.ARTIFACT_DIR / ".matbench_prom_db_dir", "w") as f:
        print(expe_name, file=f)

    with open(env.ARTIFACT_DIR / ".uuid", "w") as f:
        print(str(uuid.uuid4()), file=f)

    with open(env.ARTIFACT_DIR / "config.yaml", "w") as f:
        yaml.dump(config.ci_artifacts.config, f, indent=4)

    dump_prometheus()



# ---
def deploy_consolidated_models():
    consolidated_models = config.ci_artifacts.get_config("tests.e2e.consolidated_models")
    model_count = len(consolidated_models)
    logging.info(f"Found {model_count} models to deploy")
    for consolidated_model in consolidated_models:
        launch_deploy_consolidated_model(consolidated_model)


def launch_deploy_consolidated_model(consolidated_model):
    with env.NextArtifactDir(consolidated_model['name']):
        deploy_consolidated_model(consolidated_model)


def validate_model(namespace, model_name):
    validate_kwargs = dict(
        namespace=namespace,
        inference_service_names=[model_name],
        method=config.ci_artifacts.get_config("kserve.inference_service.validation.method"),
        dataset=config.ci_artifacts.get_config("kserve.inference_service.validation.dataset"),
        query_count=config.ci_artifacts.get_config("kserve.inference_service.validation.query_count"),
        raw_deployment=config.ci_artifacts.get_config("kserve.raw_deployment.enabled"),
    )
    if validate_kwargs["raw_deployment"]:
        validate_kwargs["proto"] = config.ci_artifacts.get_config("kserve.inference_service.validation.proto")

    run.run_toolbox("kserve", "validate_model", **validate_kwargs)


def deploy_consolidated_model(consolidated_model, namespace=None, mute_logs=None, delete_others=None, limits_equals_requests=None):
    logging.info(f"Deploying model '{consolidated_model['name']}'")

    model_name = consolidated_model["name"]

    if namespace is None:
        namespace = consolidated_model.get("namespace")

    if namespace is None:
        namespace = consolidate_model_namespace(consolidated_model)

    logging.info(f"Deploying a consolidated model. Changing the test namespace to '{namespace}'")

    if "nvidia.com/gpu_memory" in consolidated_model["serving_runtime"].get("kserve", {}).get("resource_request",{}):
        logging.info(f"Ignoring nvidia.com/gpu_memory resource request, not yet used")
        del consolidated_model["serving_runtime"]["kserve"]["resource_request"]["nvidia.com/gpu_memory"]

    if mute_logs is None:
        mute_logs = config.ci_artifacts.get_config("kserve.model.serving_runtime.mute_logs")

    if delete_others is None:
        delete_others = config.ci_artifacts.get_config("tests.e2e.delete_others")


    # first choice:  from the function arg (cli)
    # second choice: from the model settings
    # third choice:  from the configuration
    if limits_equals_requests is None:
        limits_equals_requests = consolidated_model["serving_runtime"].get("limits_equals_requests")

        if limits_equals_requests is None:
            limits_equals_requests = config.ci_artifacts.get_config("tests.e2e.limits_equals_requests")


    serving_runtime_name = consolidated_model["serving_runtime"].get("name", model_name)


    # mandatory fields
    args_dict = dict(
        namespace=namespace,
        serving_runtime_name=serving_runtime_name,
        sr_kserve_image=consolidated_model["serving_runtime"]["kserve"]["image"],
        sr_kserve_resource_request=consolidated_model["serving_runtime"]["kserve"]["resource_request"],

        sr_transformer_image=consolidated_model["serving_runtime"]["transformer"]["image"],
        sr_transformer_resource_request=consolidated_model["serving_runtime"]["transformer"]["resource_request"],
        sr_mute_logs=mute_logs,

        inference_service_name=model_name,
        inference_service_model_format=consolidated_model["inference_service"]["model_format"],
        storage_uri=consolidated_model["inference_service"]["storage_uri"],
        sa_name=config.ci_artifacts.get_config("kserve.sa_name"),

        delete_others=delete_others,
        limits_equals_requests=limits_equals_requests,
    )

    # optional fields
    try: args_dict["inference_service_min_replicas"] = consolidated_model["inference_service"]["min_replicas"]
    except KeyError: pass

    if (secret_key := consolidated_model.get("secret_key")) != None:
        import test
        secret_env_file = test.PSAP_ODS_SECRET_PATH / config.ci_artifacts.get_config("secrets.kserve_model_secret_settings")
        if not secret_env_file.exists():
            raise FileNotFoundError(f"Watsonx model secret settings file does not exist :/ {secret_env_file}")

        args_dict["secret_env_file_name"] = secret_env_file
        args_dict["secret_env_file_key"] = secret_key
    else:
        logging.warning("No secret env key defined for this model")


    if (extra_env := consolidated_model["serving_runtime"].get("transformer", {}).get("extra_env")):
        if not isinstance(extra_env, dict):
            raise ValueError(f"serving_runtime.transformer.extra_env must be a dict. Got a {extra_env.__class__.__name__}: '{extra_env}'")
        args_dict["sr_transformer_extra_env_values"] = extra_env

    if (extra_env := consolidated_model["serving_runtime"].get("kserve", {}).get("extra_env")):
        if not isinstance(extra_env, dict):
            raise ValueError(f"serving_runtime.kserve.extra_env must be a dict. Got a {extra_env.__class__.__name__}: '{extra_env}'")
        args_dict["sr_kserve_extra_env_values"] = extra_env

    args_dict["sr_container_flavor"] = consolidated_model["serving_runtime"]["container_flavor"]

    if "nvidia.com/gpu" in consolidated_model["serving_runtime"].get("kserve", {}).get("resource_request",{}):
        num_gpus = consolidated_model["serving_runtime"]["kserve"]["resource_request"]["nvidia.com/gpu"]
        if num_gpus > 1:
            args_dict["sr_shared_memory"]=True

    args_dict["raw_deployment"] = config.ci_artifacts.get_config("kserve.raw_deployment.enabled")

    with env.NextArtifactDir("prepare_namespace"):
        test_scale.prepare_user_sutest_namespace(namespace)

    try:
        deploy_model_start_ts = datetime.datetime.now()
        try:
            run.run_toolbox("kserve", "deploy_model", **args_dict)
        finally:
            deploy_model_end_ts = datetime.datetime.now()
            try:
                deploy_model_dir = list(env.ARTIFACT_DIR.glob("*__kserve__deploy_model"))[0]
            except Exception as e:
                logging.error("Faile to get the deploy directory :/", e)
                logging.info(f"Using {env.ARTIFACT_DIR} as a fallback.")
                deploy_model_dir = env.ARTIFACT_DIR

            # could be read from env.ARTIFACT_DIR / settings.yaml
            settings = dict(
                e2e_test=True,
                model_name=consolidated_model['name'],
                mode="deploy",
            )
            if (index := consolidated_model.get("index")) is not None:
                settings["index"] = index

            with open(deploy_model_dir / "test_start_end.json", "w") as f:
                json.dump(dict(
                    start=deploy_model_start_ts.astimezone().isoformat(),
                    end=deploy_model_end_ts.astimezone().isoformat(),
                    settings=settings,
                ), f, indent=4)
                print("", file=f)

        if config.ci_artifacts.get_config("tests.e2e.validate_model"):
            validate_model(namespace, model_name)

    except Exception as e:
        logging.error(f"Deployment of {model_name} failed :/ {e.__class__.__name__}: {e}")
        raise e
    finally:
        if config.ci_artifacts.get_config("tests.e2e.capture_state"):
            run.run_toolbox("kserve", "capture_state", namespace=namespace, mute_stdout=True)


def undeploy_consolidated_model(consolidated_model, namespace=None):
    if namespace is None:
        namespace = consolidated_model.get("namespace")

    if namespace is None:
        namespace = consolidate_model_namespace(consolidated_model)

    model_name = consolidated_model["name"]
    args_dict = dict(
        namespace=namespace,
        serving_runtime_name=model_name,
        inference_service_name=model_name,
    )

    run.run_toolbox("kserve", "undeploy_model", **args_dict)

def test_consolidated_models():
    consolidated_models = config.ci_artifacts.get_config("tests.e2e.consolidated_models")
    model_count = len(consolidated_models)
    logging.info(f"Found {model_count} models to test")
    for consolidated_model in consolidated_models:
        launch_test_consolidated_model(consolidated_model)

def launch_test_consolidated_model(consolidated_model, dedicated_dir=True):

    context = env.NextArtifactDir(f"test_{consolidated_model['name']}") \
        if dedicated_dir else open("/dev/null") # dummy context

    matbenchmarking = config.ci_artifacts.get_config("tests.e2e.matbenchmark.enabled")
    with context:
        settings_filename = "settings.model.yaml" if matbenchmarking else "settings.yaml"

        with open(env.ARTIFACT_DIR / settings_filename, "w") as f:
            settings = dict(
                e2e_test=True,
                model_name=consolidated_model['name'],
            )
            if (index := consolidated_model.get("index")) is not None:
                settings["index"] = index

            yaml.dump(settings, f, indent=4)

        with open(env.ARTIFACT_DIR / "config.yaml", "w") as f:
            yaml.dump(config.ci_artifacts.config, f, indent=4)

        if not matbenchmarking:
            with open(env.ARTIFACT_DIR / ".uuid", "w") as f:
                print(str(uuid.uuid4()), file=f)

        exit_code = 1
        try:
            exit_code = test_consolidated_model(consolidated_model)
        finally:
            if not matbenchmarking:
                with open(env.ARTIFACT_DIR / "exit_code", "w") as f:
                    print(f"{exit_code}", file=f)


def matbenchmark_run_llm_load_test(namespace, llm_load_test_args):
    visualize.prepare_matbench()

    with env.NextArtifactDir("matbenchmark__llm_load_test"):
        benchmark_values = {}
        test_configuration = {}

        for key, value in llm_load_test_args.items():
            if isinstance(value, list):
                benchmark_values[key] = value
            else:
                test_configuration[key] = value

        test_configuration["namespace"] = namespace

        path_tpl = "_".join([f"{k}={{settings[{k}]}}" for k in benchmark_values.keys()])

        expe_name = "expe"
        json_benchmark_file = matbenchmark.prepare_benchmark_file(
            path_tpl=path_tpl,
            script_tpl=f"{pathlib.Path(__file__).absolute()} run_one_matbench",
            stop_on_error=config.ci_artifacts.get_config("tests.e2e.matbenchmark.stop_on_error"),
            test_files={"test_config.yaml": test_configuration},
            expe_name=expe_name,
            benchmark_values=benchmark_values,
            common_settings={},
        )

        benchmark_file, content = matbenchmark.save_benchmark_file(json_benchmark_file)
        logging.info(f"Benchmark configuration to run: \n{content}")

        args = matbenchmark.set_benchmark_args(benchmark_file, expe_name)

        failed = matbenchmark.run_benchmark(args)

        if failed:
            msg = "_run_test_multiple_values: matbench benchmark failed :/"
            logging.error(msg)
            raise RuntimeError(msg)


def run_one_matbench():
    with env.TempArtifactDir(RUN_DIR):
        with open(env.ARTIFACT_DIR / "settings.yaml") as f:
            settings = yaml.safe_load(f)

        with open(env.ARTIFACT_DIR / "test_config.yaml") as f:
            test_config = yaml.safe_load(f)

        with open(env.ARTIFACT_DIR / "config.yaml", "w") as f:
            yaml.dump(config.ci_artifacts.config, f, indent=4)

        with open(env.ARTIFACT_DIR / ".uuid", "w") as f:
            print(str(uuid.uuid4()), file=f)

        namespace = test_config.pop("namespace")
        try:
            run.run_toolbox("llm_load_test", "run", **(test_config | settings))
        finally:
            if config.ci_artifacts.get_config("tests.e2e.capture_state"):
                run.run_toolbox("kserve", "capture_state", namespace=namespace, mute_stdout=True)

    sys.exit(0)


def test_consolidated_model(consolidated_model, namespace=None):
    logging.info(f"Testing model '{consolidated_model['name']}")

    model_name = consolidated_model["name"]
    if namespace is None:
        namespace = consolidated_model.get("namespace")
    if namespace is None:
        namespace = consolidate_model_namespace(consolidated_model)

    if config.ci_artifacts.get_config("tests.e2e.validate_model"):
        validate_model(namespace, model_name)

    if not (use_llm_load_test := config.ci_artifacts.get_config("tests.e2e.llm_load_test.enabled")):
        logging.info("tests.e2e.llm_load_test.enabled is not set, stopping the testing.")
        return

    if config.ci_artifacts.get_config("kserve.raw_deployment.enabled"):
        svc_name = run.run(f"oc get svc -lserving.kserve.io/inferenceservice={model_name} -ojsonpath={{.items[0].metadata.name}} -n {namespace}", capture_stdout=True).stdout
        if not svc_name:
            raise RuntimeError(f"Failed to get the hostname for Service of InferenceService {namespace}/{model_name}")
        port = 80
        host = f"{svc_name}.{namespace}.svc.cluster.local"
    else:
        host_url = run.run(f"oc get inferenceservice/{model_name} -n {namespace} -ojsonpath={{.status.url}}", capture_stdout=True).stdout
        host = host_url.lstrip("https://")
        if host == "":
            raise RuntimeError(f"Failed to get the hostname for InferenceService {namespace}/{model_name}")
        port = 443

    llm_config = config.ci_artifacts.get_config("tests.e2e.llm_load_test")

    args_dict = dict(
        host=host,
        port=port,
        duration=llm_config["duration"],
        plugin=llm_config["plugin"],
        interface=llm_config["interface"],
        model_id=model_name,
        llm_path=llm_config["src_path"],
        concurrency=llm_config["concurrency"]
    )

    if config.ci_artifacts.get_config("tests.e2e.matbenchmark.enabled"):
        matbenchmark_run_llm_load_test(namespace, args_dict)
    else:
        try:
            run.run_toolbox("llm_load_test", "run", **args_dict)
        finally:
            if config.ci_artifacts.get_config("tests.e2e.capture_state"):
                run.run_toolbox("kserve", "capture_state", namespace=namespace, mute_stdout=True)

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

        self.test_one_model = test_one_model
        self.run_one_matbench = run_one_matbench

        self.single_model_deploy_and_test_sequentially = single_model_deploy_and_test_sequentially

        self.multi_model_test_sequentially = multi_model_test_sequentially
        self.multi_model_test_concurrently = multi_model_test_concurrently

        self.rebuild_driver_image = rebuild_driver_image


def main():
    # Print help rather than opening a pager
    fire.core.Display = lambda lines, out: print(*lines, file=out)

    fire.Fire(Entrypoint())


if __name__ == "__main__":
    try:
        if not "JOB_COMPLETION_INDEX" in os.environ:
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
