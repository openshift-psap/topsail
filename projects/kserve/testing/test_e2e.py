#!/usr/bin/env python

import sys, os
import pathlib

from projects.core.library import config
TOPSAIL_DIR = pathlib.Path(config.__file__).parents[3]
TESTING_THIS_DIR = pathlib.Path(__file__).absolute().parent

RUN_DIR = pathlib.Path(os.getcwd()) # for run_one_matbench
ARTIF_DIR = os.environ.get("ARTIFACT_DIR")
print(f"STARTING test_e2e with RUN_DIR= { RUN_DIR }, ARTIFACT_DIR = { ARTIF_DIR }")

import subprocess
import logging
import datetime
import time
import json
import yaml
import uuid

import fire

PSAP_ODS_SECRET_PATH = pathlib.Path(os.environ.get("PSAP_ODS_SECRET_PATH", "/env/PSAP_ODS_SECRET_PATH/not_set"))

from projects.core.library import env, run, visualize, matbenchmark
import prepare_scale, test_scale, prepare_kserve

print(f"STARTING test_e2e with RUN_DIR= { RUN_DIR }, ARTIFACT_DIR = { ARTIF_DIR }")
os.chdir(TOPSAIL_DIR)

# ---

def consolidate_model_namespace(consolidated_model):
    namespace_prefix = config.ci_artifacts.get_config("tests.e2e.namespace")

    model_index = consolidated_model["index"]
    return f"{namespace_prefix}-{model_index}"

def consolidate_models(index=None, use_job_index=False, name=None, namespace=None, save=True):
    # name is the name field in the tests.e2e.models list used to uniquely identify it.
    consolidated_models = []
    if name and namespace:
        consolidated_models.append(consolidate_model(name=name))
    elif index is not None and name:
        consolidated_models.append(consolidate_model(index=index, name=name))
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


def consolidate_model(index=None, name=None, show=True):
    model_list = config.ci_artifacts.get_config("tests.e2e.models")
    if name is None:
        if index >= len(model_list):
            raise IndexError(f"Requested model index #{index}, but only {len(model_list)} are defined. {model_list}")

        model_config = model_list[index]
    else:
        model_config = None
        for model_def in model_list:
            if model_def.get("name") == name:
                model_config = model_def
                break

        if not model_config:
            model_config = dict(name = name)

    return prepare_scale.consolidate_model_config(model_config=model_config, index=index, show=show)

# ---

def test_ci():
    "Executes the full e2e test"

    # in the OCP CI, the config is passed from 'prepare' to 'test', so this is a NOOP
    # in the Perf CI environment, the config isn't passed, so this is mandatory.
    runtime = config.ci_artifacts.get_config("kserve.model.runtime")
    if config.ci_artifacts.get_config("kserve.model.serving_runtime.update_image"):
        prepare_kserve.update_serving_runtime_images(runtime)

    mode = config.ci_artifacts.get_config("tests.e2e.mode")
    try:
        if mode == "single":
            single_model_deploy_and_test_sequentially(locally=False)
        elif mode == "longevity":
            test_models_longevity()
        elif mode == "multi":
            multi_model_deploy_and_test()
        else:
            raise ValueError(f"Invalid value for tests.e2e.mode: {mode} :/")
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


def deploy_one_model(index: int = None, use_job_index: bool = False, model_name: str = None, namespace: str = None):
    "Deploys one of the configured models, according to the index parameter or JOB_COMPLETION_INDEX"

    consolidate_models(index=index, use_job_index=use_job_index, name=model_name, namespace=namespace)
    deploy_consolidated_models()


def multi_model_test_sequentially(locally=False):
    "Tests all the configured models sequentially (one after the other)"

    logging.info(f"Test the models sequentially (locally={locally})")
    if locally:
        with open(env.ARTIFACT_DIR / "settings.mode.yaml", "w") as f:
            yaml.dump(dict(mode="multi-model_sequential"), f, indent=4)
        consolidate_models()
        test_consolidated_models()
        return

    # launch the remote execution

    prom_start_ts = reset_prometheus()
    with env.NextArtifactDir("multi_model_test_sequentially"):
        try:
            run.run_toolbox_from_config("local_ci", "run_multi", suffix="test_sequentially",
                                        artifact_dir_suffix="_test_sequentially")
        finally:
            generate_prom_results("multi-model_sequential", prom_start_ts)


def test_models_longevity():
    import pandas as pd # no need to import it in the main scope, takes long to load ...
    sleep_interval = pd.Timedelta(config.ci_artifacts.get_config("tests.e2e.longevity.sleep_interval"))
    total_duration = pd.Timedelta(config.ci_artifacts.get_config("tests.e2e.longevity.total_duration"))
    test_on_finish = config.ci_artifacts.get_config("tests.e2e.longevity.test_on_finish")

    start = datetime.datetime.now()
    finish = start + total_duration
    logging.info(f"Longevity test started at:     {start}")
    logging.info(f"Longevity test will finish at: {finish}")

    prom_start_ts = reset_prometheus()

    deploy_models_concurrently()

    run_final_test = False

    watch_file = env.ARTIFACT_DIR / "stop"
    watch_file.unlink(missing_ok=True)
    logging.info(f"Touch {watch_file} to gracefully interrupt the longevity testing.")

    i = -1
    while datetime.datetime.now() < finish or run_final_test:
        i += 1
        expe_name = f"longevity_{i}"
        with env.NextArtifactDir(expe_name):
            with open(env.ARTIFACT_DIR / "settings.longevity.yaml", "w") as f:
                yaml.dump(dict(longevity_index=i), f, indent=4)

            logging.info(f"Running test {i} ...")
            multi_model_test_concurrently(expe_name, with_kserve_prom=False)

            if datetime.datetime.now() > finish:
                what = "Final test finished" if run_final_test else f"Test {i} finished after the deadline"
                logging.info(f"{what}. Done with the longevity testing.")
                break

            assert not run_final_test

            test_end = datetime.datetime.now()
            logging.info(f"Test {i} finished at: {test_end}")

            next_start = test_end + sleep_interval
            if next_start > finish:
                logging.info(f"Test {i+1} would start too late ({next_start}).")
                if not test_on_finish:
                    logging.info(f"test_on_finish not set, all done.")
                    break
                logging.info(f"test_on_finish set. Running one more test.")
                run_final_test = True
                next_start = finish

            logging.info(f"Test {i+1} starts at:   {next_start} (in {next_start - datetime.datetime.now()})")
            logging.info(f"Longevity test ends at:   {finish} (in {finish - datetime.datetime.now()})")

            logging.info(f"Touch {watch_file} to gracefully interrupt the longevity testing.")

            while datetime.datetime.now() < next_start:
                if not watch_file.exists():
                    time.sleep(30)

                if not watch_file.exists():
                    continue

                logging.warning(f"{watch_file} exists, stopping gracefully the longevity test.")
                finish = test_end
                run_final_test = False
                break

    generate_prom_results("longevity", prom_start_ts)


def multi_model_deploy_and_test():
    deploy_models_concurrently()

    multi_model_test_concurrently()
    multi_model_test_sequentially(locally=False)


def single_model_deploy_and_test_sequentially(locally=False):
    "Deploy and test all the configured models sequentially (one after the other)"

    logging.info(f"Deploy and test the models sequentially (locally={locally})")
    if not locally:
        return run.run_toolbox_from_config("local_ci", "run_multi", suffix="deploy_and_test_sequentially", artifact_dir_suffix="_e2e_perf_test")


    with open(env.ARTIFACT_DIR / "settings.mode.yaml", "w") as f:
        yaml.dump(dict(mode="single-model"), f, indent=4)

    namespace = config.ci_artifacts.get_config("tests.e2e.namespace") + "-perf"
    consolidated_models = consolidate_models(namespace=namespace)

    run.run_toolbox("kserve", "undeploy_model", namespace=namespace, all=True,
                    artifact_dir_suffix="_all")

    exc = None
    failed = []
    for consolidated_model in consolidated_models:
        with env.NextArtifactDir(consolidated_model['name']):
            prom_start_ts = reset_prometheus()
            try:

                deploy_consolidated_model(consolidated_model)

                launch_test_consolidated_model(consolidated_model, dedicated_dir=False)
            except Exception as e:
                failed += [consolidated_model['name']]
                with open(env.ARTIFACT_DIR / "FAILURE", "a") as f:
                    print(f"{consolidated_model['name']} failed: {e.__class__.__name__}: {e}", file=f)
                exc = e

            generate_prom_results("single_model", prom_start_ts)

            run.run_and_catch(exc, undeploy_consolidated_model, consolidated_model)

    if failed:
        logging.fatal(f"single_model_deploy_and_test_sequentially: {len(failed)} tests failed :/ {' '.join(failed)}")
        raise exc


def multi_model_test_concurrently(expe_name="multi-model_concurrent", with_kserve_prom=True):
    "Tests all the configured models concurrently (all at the same time)"

    if with_kserve_prom:
        prom_start_ts = reset_prometheus()

    with env.NextArtifactDir("multi_model_test_concurrently"):
        try:
            logging.info(f"Test the models concurrently ({expe_name})")
            run.run_toolbox_from_config("local_ci", "run_multi", suffix="test_concurrently", artifact_dir_suffix="_test_concurrently")
        finally:
            if with_kserve_prom:
                generate_prom_results(expe_name, prom_start_ts)


def test_one_model(
        index: int = None,
        use_job_index: bool = False,
        model_name: str = None,
        namespace: str = None,
        do_visualize: bool = None,
        capture_prom = None,
):
    "Tests one of the configured models, according to the index parameter or JOB_COMPLETION_INDEX"

    if use_job_index:
        with open(env.ARTIFACT_DIR / "settings.mode.yaml", "w") as f:
            yaml.dump(dict(mode="multi-model_concurrent"), f, indent=4)

    if capture_prom is not None:
        config.ci_artifacts.set_config("tests.capture_prom", capture_prom)

    if namespace is not None:
        config.ci_artifacts.set_config("tests.e2e.namespace", namespace)

    prom_start_ts = reset_prometheus()

    consolidate_models(index=index, use_job_index=True, name=model_name, namespace=namespace)
    test_consolidated_models()

    generate_prom_results("test_one_model", prom_start_ts)

    if do_visualize is None:
        do_visualize = config.ci_artifacts.get_config("tests.visualize")

    if not do_visualize:
        logging.info("Not generating the visualization because it isn't activated.")
    else:
        results_dir = env.ARTIFACT_DIR
        with env.NextArtifactDir("plots"):
            visualize.prepare_matbench()
            import test
            test.generate_plots(results_dir)

        run.run(f"testing/utils/generate_plot_index.py > {env.ARTIFACT_DIR}/reports_index.html", check=False)

# ---

def reset_prometheus(delay=60):
    capture_prom = config.ci_artifacts.get_config("tests.capture_prom")
    if not capture_prom:
        logging.info("tests.capture_prom is disabled, skipping Prometheus DB reset")
        return

    prom_start_ts = datetime.datetime.now()

    if capture_prom == "with-queries":
        return prom_start_ts

    with run.Parallel("cluster__reset_prometheus_dbs") as parallel:
        parallel.delayed(run.run_toolbox, "cluster", "reset_prometheus_db", mute_stdout=True)
        if config.ci_artifacts.get_config("tests.capture_prom_uwm"):
            parallel.delayed(run.run_toolbox_from_config, "cluster", "reset_prometheus_db", suffix="uwm", artifact_dir_suffix="_uwm", mute_stdout=True)

    logging.info(f"Wait {delay}s for Prometheus to restart collecting data ...")
    time.sleep(delay)

    # at the moment, only used when capture_prom == "with-queries".
    # Returned for consistency.
    return prom_start_ts


def dump_prometheus(prom_start_ts, delay=60):
    capture_prom = config.ci_artifacts.get_config("tests.capture_prom")

    if not capture_prom:
        logging.info("tests.capture_prom is disabled, skipping Prometheus DB dump")
        return

    if config.ci_artifacts.get_config("tests.dry_mode"):
        logging.info("tests.dry_mode is enabled, skipping Prometheus DB dump")
        return

    if capture_prom == "with-queries":
        if config.ci_artifacts.get_config("tests.capture_prom_uwm"):
            logging.error("tests.capture_prom_uwm not supported with capture Prom with queries")

        prom_end_ts = datetime.datetime.now()
        args = dict(
            duration_s = (prom_end_ts - prom_start_ts).total_seconds(),
            promquery_file = TESTING_THIS_DIR / "metrics.txt",
            dest_dir = env.ARTIFACT_DIR / "metrics",
            namespace = config.ci_artifacts.get_config("tests.e2e.namespace"),
        )

        with env.NextArtifactDir("cluster__dump_prometheus_dbs"):
            run.run_toolbox("cluster", "query_prometheus_db", **args)
            with env.NextArtifactDir("cluster__dump_prometheus_db"):
                with open(env.ARTIFACT_DIR / "prometheus.tar.dummy", "w") as f:
                    print(f"""This file is a dummy.
Metrics have been queried from Prometheus and saved into {args['dest_dir']}.
Keep this file here, so that 'projects/fine_tuning/visualizations/fine_tuning_prom/store/parsers.py' things Prometheus metrics have been captured,
and it directly processes the cached files from the metrics directory.""", file=f)
                nodes = run.run("oc get nodes -ojson", capture_stdout=True)
                with open(env.ARTIFACT_DIR / "nodes.json", "w") as f:
                    print(nodes.stdout.strip(), file=f)

        return

    # prom_start_ts not used when during full prometheus dump.

    logging.info(f"Wait {delay}s for Prometheus to finish collecting data ...")
    time.sleep(delay)

    with run.Parallel("cluster__dump_prometheus_dbs") as parallel:
        parallel.delayed(run.run_toolbox, "cluster", "dump_prometheus_db", mute_stdout=True)
        if config.ci_artifacts.get_config("tests.capture_prom_uwm"):
            parallel.delayed(run.run_toolbox_from_config, "cluster", "dump_prometheus_db", suffix="uwm", artifact_dir_suffix="_uwm", mute_stdout=True)


def generate_prom_results(expe_name, prom_start_ts):
    anchor_file = env.ARTIFACT_DIR / ".matbench_prom_db_dir"
    if anchor_file.exists():
        raise ValueError(f"File {anchor_file} already exist. It should be in a dedicated directory.")

    # flag file for kserve-prom visualization
    with open(anchor_file, "w") as f:
        print(expe_name, file=f)

    with open(env.ARTIFACT_DIR / ".uuid", "w") as f:
        print(str(uuid.uuid4()), file=f)

    with open(env.ARTIFACT_DIR / "config.yaml", "w") as f:
        yaml.dump(config.ci_artifacts.config, f, indent=4)

    dump_prometheus(prom_start_ts)

    raw_deployment = config.ci_artifacts.get_config("kserve.raw_deployment.enabled")
    run.run_toolbox("kserve", "capture_operators_state", raw_deployment=raw_deployment, run_kwargs=dict(capture_stdout=True))

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


def validate_model(namespace, *, model_name, inference_service_names, runtime, artifact_dir_suffix=None):
    #if model_name and inference_service_names:
    #    raise ValueError("validate_model: cannot receive model_name and inference_service_names")
    #if not (model_name or inference_service_names):
    #    raise ValueError("validate_model: must receive model_name or inference_service_names")

    validate_kwargs = dict(
        namespace=namespace,
        inference_service_names=inference_service_names,
        model_id=model_name,
        runtime=runtime,
        query_count=config.ci_artifacts.get_config("kserve.inference_service.validation.query_count"),
        raw_deployment=config.ci_artifacts.get_config("kserve.raw_deployment.enabled"),
        method=config.ci_artifacts.get_config("kserve.inference_service.validation.method")
    )

    validate_kwargs["proto"] = config.ci_artifacts.get_config("kserve.inference_service.validation.proto")

    validate_kwargs["artifact_dir_suffix"] = artifact_dir_suffix
    validate_kwargs["runtime"] = runtime

    run.run_toolbox("kserve", "validate_model", **validate_kwargs)


def deploy_consolidated_model(consolidated_model, namespace=None, mute_logs=None, delete_others=None, limits_equals_requests=None):
    logging.info(f"Deploying model '{consolidated_model['name']}'")

    model_name = consolidated_model["name"]

    if namespace is None:
        namespace = consolidated_model.get("namespace")

    if namespace is None:
        namespace = consolidate_model_namespace(consolidated_model)

    logging.info(f"Deploying a consolidated model. Changing the test namespace to '{namespace}'")

    if delete_others is None:
        delete_others = config.ci_artifacts.get_config("tests.e2e.delete_others")

    #TODO
    #if limits_equals_requests is None:
    #    limits_equals_requests = consolidated_model["serving_runtime"].get("limits_equals_requests")

    #    if limits_equals_requests is None:
    #        limits_equals_requests = config.ci_artifacts.get_config("tests.e2e.limits_equals_requests")

    # mandatory fields
    args_dict = dict(
        namespace=namespace,
        runtime=consolidated_model["runtime"],
        model_name=consolidated_model["model"],
        sr_name=consolidated_model["runtime"],
        sr_kserve_image=consolidated_model["serving_runtime"]["kserve"]["image"],
        inference_service_name=consolidated_model["name"],
        delete_others=delete_others,
        #limits_equals_requests=limits_equals_requests
    )

    # optional fields
    try: args_dict["inference_service_min_replicas"] = consolidated_model["inference_service"]["min_replicas"]
    except KeyError: pass

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
                logging.exception("Failed to get the deploy directory:%s", e)
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

# python3.9 run_toolbox.py kserve validate_model '--inference_service_names=["mpt-7b-instruct2-isvc"]' --method="none" --query_count=3 --runtime="vllm" --model_id=flan-t5-xl --namespace=watsonx-e2e-perf --raw_deployment=True --proto=projects/kserve/testing/protos/tgis_generation.proto

        if config.ci_artifacts.get_config("tests.e2e.validate_model"):
            validate_model(namespace, inference_service_names=[args_dict["inference_service_name"]], model_name=model_name, runtime=args_dict["runtime"])

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
        sr_name=model_name,
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

        logging.info("Putting settings files in ARTIFACT_DIR: %s", env.ARTIFACT_DIR)
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

        with open(env.ARTIFACT_DIR / "consolidated_model.yaml", "w") as f:
            yaml.dump(consolidated_model, f, indent=4)

        exit_code = 1
        try:
            exit_code = test_consolidated_model(consolidated_model)
        finally:
            if not matbenchmarking:
                with open(env.ARTIFACT_DIR / "exit_code", "w") as f:
                    print(f"{exit_code}", file=f)


def matbenchmark_run_llm_load_test(namespace, llm_load_test_args, model_max_concurrency):
    visualize.prepare_matbench()

    with env.NextArtifactDir("matbenchmark__llm_load_test"):
        benchmark_values = {}
        test_configuration = {}

        for key, value in llm_load_test_args.items():
            if isinstance(value, list):
                if key == "concurrency" and model_max_concurrency:
                    benchmark_values[key] = [v for v in value if v <= model_max_concurrency]
                    if len(benchmark_values[key]) != len(value):
                        logging.warning(f"Removed the concurrency levels higher than {model_max_concurrency}.")
                else:
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
    cwd = pathlib.Path(os.getcwd()) # for run_one_matbench
    logging.info("In run_one_matbench. CWD: %s, RUN_DIR: %s, ARTIFACT_DIR: %s", cwd, RUN_DIR, env.ARTIFACT_DIR)

    with env.TempArtifactDir(RUN_DIR):
        with open(env.ARTIFACT_DIR / "settings.yaml") as f:
            settings = yaml.safe_load(f)

        with open(env.ARTIFACT_DIR / "test_config.yaml") as f:
            test_config = yaml.safe_load(f)

        llm_load_test_cfg = (test_config | settings)

        config.ci_artifacts.set_config("tests.e2e.llm_load_test.args.concurrency",
                                       llm_load_test_cfg["concurrency"])

        with open(env.ARTIFACT_DIR / "config.yaml", "w") as f:
            yaml.dump(config.ci_artifacts.config, f, indent=4)

        with open(env.ARTIFACT_DIR / ".uuid", "w") as f:
            print(str(uuid.uuid4()), file=f)

        namespace = llm_load_test_cfg.pop("namespace")
        try:
            run.run_toolbox("llm_load_test", "run", **llm_load_test_cfg)
        finally:
            if config.ci_artifacts.get_config("tests.e2e.capture_state"):
                run.run_toolbox("kserve", "capture_state", namespace=namespace, mute_stdout=True)

    sys.exit(0)


def test_consolidated_model(consolidated_model, namespace=None):
    logging.info(f"Testing model '{consolidated_model['name']}")

    inference_service_name = consolidated_model["name"]
    model_name = consolidated_model["model"]
    if namespace is None:
        namespace = consolidated_model.get("namespace")
    if namespace is None:
        namespace = consolidate_model_namespace(consolidated_model)

    if config.ci_artifacts.get_config("tests.e2e.validate_model"):
        validate_model(namespace, inference_service_names=[inference_service_name], model_name=model_name, runtime=consolidated_model["runtime"])

    if not (config.ci_artifacts.get_config("tests.e2e.llm_load_test.enabled")):
        logging.info("tests.e2e.llm_load_test.enabled is not set, stopping the testing.")
        return

    llm_load_test_args = config.ci_artifacts.get_config("tests.e2e.llm_load_test.args")

    if config.ci_artifacts.get_config("kserve.raw_deployment.enabled"):
        svc_name = run.run(f"oc get svc -lserving.kserve.io/inferenceservice={inference_service_name} -ojsonpath={{.items[0].metadata.name}} -n {namespace}", capture_stdout=True).stdout
        if not svc_name:
            raise RuntimeError(f"Failed to get the hostname for Service of InferenceService {namespace}/{model_name}")

        # TODO this should probably be based on whether we are using http or gRPC.
        if config.ci_artifacts.get_config("kserve.model.runtime") == "vllm":
            port = 8080
        else: # Assume TGIS gRPC
            port = 8033

        host = f"{svc_name}.{namespace}.svc.cluster.local"
    else:
        host_url = run.run(f"oc get inferenceservice/{inference_service_name} -n {namespace} -ojsonpath={{.status.components.predictor.url}}", capture_stdout=True).stdout
        # In validate we use oc get ksvc \
        # -lserving.kserve.io/inferenceservice={{ kserve_validate_model_inference_service_name }} \
        # -n {{ kserve_validate_model_namespace }} -ojsonpath='{.items[0].status.url}'
        host = host_url.removeprefix("https://")
        if host == "":
            raise RuntimeError(f"Failed to get the hostname for InferenceService {namespace}/{inference_service_name}")
        port = 443

        if llm_load_test_args.get("plugin") == "tgis_grpc_plugin":
            llm_load_test_args["use_tls"] = True

    # small if not set
    size_name = consolidated_model.get("testing", {}).get("size", "small")

    model_max_concurrency = consolidated_model.get("testing", {}).get("max_concurrency", 16)

    llm_load_test_dataset_sample_args = config.ci_artifacts.get_config(f"tests.e2e.llm_load_test.dataset_size.{size_name}")
    llm_load_test_args |= llm_load_test_dataset_sample_args

    if llm_load_test_args.get("plugin") == "openai_plugin":
        model_name = "/mnt/models/"

    args_dict = dict(
        host=host,
        port=port,
        model_id=model_name,

        **llm_load_test_args
    )

    if config.ci_artifacts.get_config("tests.e2e.matbenchmark.enabled"):
        matbenchmark_run_llm_load_test(namespace, args_dict, model_max_concurrency)
    elif model_max_concurrency and args_dict["concurrency"] > model_max_concurrency:
        logging.warning(f"Requested concurrency ({args_dict['concurrency']}) is higher than the model limit ({model_max_concurrency})")
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
        from test import init
        init(ignore_secret_path=True, apply_preset_from_pr_args=True)

        sys.exit(main())
    except subprocess.CalledProcessError as e:
        logging.error(f"Command '{e.cmd}' failed --> {e.returncode}")
        sys.exit(1)
    except KeyboardInterrupt:
        print() # empty line after ^C
        logging.error(f"Interrupted.")
        sys.exit(1)
