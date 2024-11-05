import sys, os
import logging
import traceback
import copy
import pathlib
import yaml
import uuid
import time
import threading
import traceback
import datetime
import json
from collections import defaultdict

from projects.core.library import env, config, run, merge_dicts
from projects.matrix_benchmarking.library import visualize, matbenchmark
from projects.rhods.library import prepare_rhoai as prepare_rhoai_mod
from projects.cluster.library import prom

import prepare_finetuning

TESTING_THIS_DIR = pathlib.Path(__file__).absolute().parent
TOPSAIL_DIR = pathlib.Path(config.__file__).parents[3]
RUN_DIR = pathlib.Path(os.getcwd()) # for run_one_matbench
os.chdir(TOPSAIL_DIR)


def generate_prom_results(expe_name, prom_start_ts):
    anchor_file = env.ARTIFACT_DIR / ".matbench_prom_db_dir"
    if anchor_file.exists():
        raise ValueError(f"File {anchor_file} already exist. It should be in a dedicated directory.")

    # flag file for fine-tuning-prom visualization
    with open(anchor_file, "w") as f:
        print(expe_name, file=f)

    with open(env.ARTIFACT_DIR / ".uuid", "w") as f:
        print(str(uuid.uuid4()), file=f)

    with open(env.ARTIFACT_DIR / "config.yaml", "w") as f:
        yaml.dump(config.project.config, f, indent=4)

    namespace = config.project.get_config("tests.fine_tuning.namespace")
    prom.dump_prometheus(prom_start_ts, namespace, TESTING_THIS_DIR)

    if (config.project.get_config("tests.capture_state")
        and not config.project.get_config("tests.dry_mode")
        ):
        run.run_toolbox("rhods", "capture_state", mute_stdout=True)
        run.run_toolbox("cluster", "capture_environment", mute_stdout=True)


def prepare_matbench_test_files(job_index=None):

    with open(env.ARTIFACT_DIR / "settings.yaml", "w") as f:
        settings = dict(
            fine_tuning=True,
        )
        if job_index is not None:
            settings["job_index"] = job_index

        yaml.dump(settings, f, indent=4)

        with open(env.ARTIFACT_DIR / "config.yaml", "w") as f:
            yaml.dump(config.project.config, f, indent=4)

        with open(env.ARTIFACT_DIR / ".uuid", "w") as f:
            print(str(uuid.uuid4()), file=f)


def _run_test(test_artifact_dir_p, test_override_values, job_index=None):
    dry_mode = config.project.get_config("tests.dry_mode")

    test_settings = config.project.get_config("tests.fine_tuning.test_settings") | test_override_values
    do_multi_model = config.project.get_config("tests.fine_tuning.multi_model.enabled")
    do_many_model = config.project.get_config("tests.fine_tuning.many_model.enabled")
    do_fms = config.project.get_config("tests.fine_tuning.fms.enabled")
    do_quality_evaluation = config.project.get_config("tests.fine_tuning.quality_evaluation.enabled")
    do_ray = config.project.get_config("tests.fine_tuning.ray.enabled")

    test_settings["hyper_parameters"] = {k: v for k, v in test_settings["hyper_parameters"].items()
                                         if v is not None}

    logging.info(f"Test configuration to run: \n{yaml.dump(test_settings, sort_keys=False)}")

    sources = config.project.get_config(f"fine_tuning.sources")
    if test_settings["dataset_name"]:
        dataset_source = sources[test_settings["dataset_name"]]

        if transform := dataset_source.get("transform", False):
            test_settings["dataset_transform"] = transform

        if (prefer_cache := dataset_source.get("prefer_cache")) is not None:
            test_settings["dataset_prefer_cache"] = prefer_cache

        if (response_template := dataset_source.get("response_template")) is not None:
            test_settings["dataset_response_template"] = response_template

    remove_none_values(test_settings)

    prepare_finetuning.prepare_namespace(test_settings)
    failed = True

    _start_ts = datetime.datetime.now()
    start_ts = None
    if not do_multi_model:
        prom_start_ts = prom.reset_prometheus()

    if do_fms:
        test_dir_name = "fms_fine_tuning"
    elif do_quality_evaluation:
        test_dir_name = "evaluate_quality"
    elif do_ray:
        workload = config.project.get_config("tests.fine_tuning.ray.workload")
        test_dir_name = f"ray__{workload}"

    with env.NextArtifactDir(test_dir_name):
        test_artifact_dir_p[0] = env.ARTIFACT_DIR

        prepare_matbench_test_files(job_index)

        try:
            if dry_mode:
                logging.info(f"tests.dry_mode is enabled, NOT running with {test_settings} | {do_multi_model=} | {do_many_model=} | {do_quality_evaluation=}")
            elif do_many_model:
                _run_test_many_model(test_settings)
            elif do_quality_evaluation:
                _run_test_quality_evaluation(test_settings)
            else:
                start_ts = _start_ts
                with open(env.ARTIFACT_DIR / "settings.mode.yaml", "w") as f:
                    yaml.dump(dict(mode="single-model"), f, indent=4)

                if do_fms:
                    test_settings["model_name"] = prepare_finetuning.get_safe_model_name(test_settings["model_name"])
                    run.run_toolbox_from_config("fine_tuning", "run_fine_tuning_job",
                                                extra=test_settings)
                elif do_ray:
                    run.run_toolbox_from_config(
                        "fine_tuning", "ray_fine_tuning_job",
                        extra=test_settings,
                    )

            failed = False
        finally:
            with open(env.ARTIFACT_DIR / "exit_code", "w") as f:
                print(1 if failed else 0, file=f)

            if start_ts:
                save_test_start_end(start_ts, test_settings)

            exc = None
            if not do_multi_model:
                exc = run.run_and_catch(exc, generate_prom_results, "single-model", prom_start_ts)

            if config.project.get_config("tests.capture_state"):
                exc = run.run_and_catch(exc, run.run_toolbox, "cluster", "capture_environment", mute_stdout=True)
                exc = run.run_and_catch(exc, run.run_toolbox, "rhods", "capture_state", mute_stdout=True)

            if exc:
                logging.warning(f"Test configuration crashed ({exc}): \n{yaml.dump(test_settings, sort_keys=False)}")

                raise exc

    if failed:
        logging.warning(f"Test configuration failed: \n{yaml.dump(test_settings, sort_keys=False)}")


    return failed


def _run_test_multi_model(test_artifact_dir_p):
    if (model_name := config.project.get_config("tests.fine_tuning.test_settings.model_name")) is not None:
        logging.warning(f"tests.fine_tuning.test_settings.model_name should be 'null' for the multi-model test. Current value ({model_name}) ignored.")

    multi_models = config.project.get_config("tests.fine_tuning.multi_model.models")

    failed = False

    lock = threading.Lock()
    counter_p = [0]
    def run_in_env(job_index, model_name):
        safe_model_name = prepare_finetuning.get_safe_model_name(model_name)
        job_name = f"job-{job_index}-{safe_model_name}"
        with env.NextArtifactDir(f"multi_model_{safe_model_name}", lock=lock, counter_p=counter_p):
            test_failed = _run_test([None], dict(model_name=model_name, name=job_name), job_index=job_index)

        if test_failed:
            logging.warning(f"_run_test_multi_model: test {job_name=} failed :/")
            nonlocal failed
            with lock:
                failed = True

    prom_start_ts = prom.reset_prometheus()

    with env.NextArtifactDir("multi_model"):
        test_artifact_dir_p[0] = env.ARTIFACT_DIR

        try:
            job_index = 0
            with env.NextArtifactDir("multi_model_reference"):
                with open(env.ARTIFACT_DIR / "settings.mode.yaml", "w") as f:
                    yaml.dump(dict(mode="multi-model_reference"), f, indent=4)

                for model in multi_models:
                    run_in_env(job_index, model["name"])
                    job_index += model.get("replicas", 1)

            job_index = 0
            with run.Parallel("multi_model_concurrent", dedicated_dir=True, exit_on_exception=False) as parallel:
                with open(env.ARTIFACT_DIR / "settings.mode.yaml", "w") as f:
                    yaml.dump(dict(mode="multi-model_concurrent"), f, indent=4)

                for model in multi_models:
                    for idx in range(model.get("replicas", 1)):
                        parallel.delayed(run_in_env, job_index, model["name"])
                        job_index += 1
            logging.info(f"Parallel multi-model test code completed successfully")

        except Exception as e:
            logging.error(f"Parallel multi-model test code throw an exception: {e}")
            traceback.print_exc()

            with lock:
                failed = True
        finally:
            generate_prom_results("multi-model", prom_start_ts)

    return failed

def _run_test_quality_evaluation(test_settings):
    test_settings["model_name"] = prepare_finetuning.get_safe_model_name(test_settings["model_name"])
    test_settings.pop("dataset_name")
    test_settings.pop("dataset_replication")

    test_settings["container_image"] = config.project.get_config("tests.fine_tuning.quality_evaluation.image")
    run.run_toolbox_from_config("fine_tuning", "run_quality_evaluation",
                                extra=test_settings)


def _run_test_and_visualize(test_override_values=None):
    failed = True
    do_matbenchmarking = test_override_values is None and config.project.get_config("tests.fine_tuning.matbenchmarking.enabled")
    do_multi_model = config.project.get_config("tests.fine_tuning.multi_model.enabled")

    ray_enabled = config.project.get_config("tests.fine_tuning.ray.enabled")
    fms_enabled = config.project.get_config("tests.fine_tuning.fms.enabled")
    quality_enabled = config.project.get_config("tests.fine_tuning.quality_evaluation.enabled")

    enabled = sum(1 for opt in (fms_enabled, quality_enabled, ray_enabled) if opt)
    if enabled != 1:
        msg = f"FMS or Quality or Ray testing must be enabled. Found {enabled} enabled. Cannot proceed."
        logging.error(msg)
        raise RuntimeError(msg)

    if not do_matbenchmarking and config.project.get_config("tests.fine_tuning.test_extra_settings"):
        msg = "Cannot use 'test_extra_settings' when 'tests.fine_tuning.tests.fine_tuning.matbenchmarking' isn't enabled."
        logging.error(msg)
        raise ValueError(msg)

    if do_matbenchmarking and do_multi_model:
        msg = "Cannot do matbenchmarking and multi-model at the same time"
        logging.error(msg)
        raise ValueError(msg)

    if not prepare_rhoai_mod.is_rhoai_installed():
        msg = "RHOAI not installed, cluster not prepared for fine-tuning"
        logging.error(msg)
        raise RuntimeError(msg)

    if fms_enabled and not prepare_rhoai_mod.is_component_deployed("trainingoperator"):
        msg = "Training Operator not enabled, cluster not prepared for fine-tuning"
        logging.error(msg)
        raise RuntimeError(msg)

    if ray_enabled and not prepare_rhoai_mod.is_component_deployed("ray"):
        msg = "Ray Operator not enabled, cluster not prepared for fine-tuning"
        logging.error(msg)
        raise RuntimeError(msg)

    test_artifact_dir_p = [None]
    try:
        if do_multi_model:
            logging.info("_run_test_and_visualize: testing in multi-model mode")
            failed = _run_test_multi_model(test_artifact_dir_p)

        elif do_matbenchmarking:
            logging.info("_run_test_and_visualize: testing in matbenchmarking mode")
            failed = _run_test_matbenchmarking(test_artifact_dir_p)

        else:
            logging.info("_run_test_and_visualize: testing in single-model mode")
            if test_override_values is None:
                test_override_values = config.project.get_config("tests.fine_tuning.test_settings")
            failed = _run_test(test_artifact_dir_p, test_override_values)

    finally:
        dry_mode = config.project.get_config("tests.dry_mode")
        if not config.project.get_config("tests.visualize"):
            logging.info(f"Visualization disabled.")

        elif dry_mode:
            logging.info(f"Running in dry mode, skipping the visualization.")

        elif test_artifact_dir_p[0] is not None:
            generate_visualization(do_matbenchmarking, test_artifact_dir_p[0])

        else:
            logging.warning("Not generating the visualization as the test artifact directory hasn't been set.")

    logging.info(f"_run_test_and_visualize: Test {'failed' if failed else 'passed'}.")

    return failed


def generate_visualization(do_matbenchmarking, test_artifact_dir):
    exc = None

    with env.NextArtifactDir("plots"):
        if do_matbenchmarking:
            visu_file = config.project.get_config("tests.fine_tuning.matbenchmarking.visu_file")
            with config.TempValue(config.project, "matbench.config_file", visu_file):
                exc = run.run_and_catch(exc, visualize.generate_from_dir, test_artifact_dir)

        else:
            exc = run.run_and_catch(exc, visualize.generate_from_dir, test_artifact_dir)

    prom_workload = config.project.get_config("matbench.prom_workload")
    capture_prom = config.project.get_config("tests.capture_prom")

    if not prom_workload or not capture_prom:
        if not capture_prom:
            logging.info(f"Setting tests.capture_prom is disabled, skipping Prometheus visualization.")
        else:
            logging.info(f"Setting matbench.prom_workload isn't set, nothing else to generate.")

        if exc:
            raise exc

        return

    index = config.project.get_config("matbench.lts.opensearch.index")
    prom_index_suffix = config.project.get_config("matbench.lts.opensearch.prom_index_suffix")
    with (
            env.NextArtifactDir("prom_plots"),
            config.TempValue(config.project, "matbench.workload", prom_workload),
            config.TempValue(config.project, "matbench.lts.opensearch.index", f"{index}{prom_index_suffix}")
    ):
        logging.info(f"Generating the plots with workload={prom_workload}")

        exc = run.run_and_catch(exc, visualize.generate_from_dir, test_artifact_dir)

    if exc:
        raise exc


def test(dry_mode=None, do_visualize=None, capture_prom=None):
    """
    Runs a fine-tuning test

    Args:
      dry_mode: if True, do not execute the tests, only list what would be executed
      visualize: if False, do not generate the visualization reports
      capture_prom: if False, do not capture Prometheus database
    """

    if dry_mode is not None:
        config.project.set_config("tests.dry_mode", dry_mode)
    if do_visualize is not None:
        config.project.set_config("tests.visualize", do_visualize)
    if capture_prom is not None:
        config.project.set_config("tests.capture_prom", capture_prom)

    try:
        failed = _run_test_and_visualize()
        return failed
    except Exception as e:
        logging.error(f"*** Caught an exception during _run_test_and_visualize: {e.__class__.__name__}: {e}")
        traceback.print_exc()

        with open(env.ARTIFACT_DIR / "FAILURE", "w") as f:
            print(traceback.format_exc(), file=f)

        raise


def _run_test_matbenchmarking(test_artifact_dir_p):
    with env.NextArtifactDir("matbenchmarking"):
        test_settings = config.project.get_config("tests.fine_tuning.test_settings")
        test_artifact_dir_p[0] = env.ARTIFACT_DIR

        test_extra_settings_lst = config.project.get_config("tests.fine_tuning.test_extra_settings")
        expe_to_run = dict()

        names = defaultdict(int)
        for idx, test_extra_settings in enumerate(test_extra_settings_lst or [None]):
            benchmark_values = copy.deepcopy(test_settings)
            if test_extra_settings is not None:
                merge_dicts(benchmark_values, test_extra_settings)

            remove_none_values(benchmark_values)

            name = benchmark_values["name"]
            names[name] += 1
            cnt = names[name] - 1

            expe_name = f"{name}_{idx}" if cnt != 0 else name

            hyper_parameters = benchmark_values.pop("hyper_parameters", {})

            for k, v in hyper_parameters.items():
                benchmark_values[f"hyper_parameters.{k}"] = v

            # reapply to ensure that the 'test_extra_settings' are applied on top of the test_settings
            if test_extra_settings is not None:
                merge_dicts(benchmark_values, test_extra_settings)

            expe_to_run[expe_name] = benchmark_values

        path_tpl = "{settings[name]}"

        json_benchmark_file = matbenchmark.prepare_benchmark_file(
            path_tpl=path_tpl,
            script_tpl=f"{sys.argv[0]} matbench_run_one",
            stop_on_error=config.project.get_config("tests.fine_tuning.matbenchmarking.stop_on_error"),
            common_settings=dict(),
            test_files={},
            expe_to_run=expe_to_run,
        )

        logging.info(f"Benchmark configuration to run: \n{yaml.dump(json_benchmark_file, sort_keys=False)}")

        benchmark_file, yaml_content = matbenchmark.save_benchmark_file(json_benchmark_file)

        args = matbenchmark.set_benchmark_args(benchmark_file)

        failed = matbenchmark.run_benchmark(args)
        if failed:
            logging.error(f"_run_test_matbenchmarking: matbench benchmark failed :/")

    return failed


def save_test_start_end(start_ts, settings, end_ts=None):
    if end_ts is None:
        end_ts = datetime.datetime.now()

    with open(env.ARTIFACT_DIR / "test_start_end.json", "w") as f:
        json.dump(dict(
            start=start_ts.astimezone().isoformat(),
            end=end_ts.astimezone().isoformat(),
            settings=settings,
        ), f, indent=4)

        print("", file=f)


def remove_none_values(d):
    for k in list(d.keys()):
        v = d[k]
        if v is None or v is {}:
            del d[k]
        elif isinstance(v, dict):
            remove_none_values(d[k])
            if not d[k]:
                del d[k]


def matbench_run_one():
    with env.TempArtifactDir(RUN_DIR):
        with open(env.ARTIFACT_DIR / "settings.yaml") as f:
            settings = yaml.safe_load(f)

        with open(env.ARTIFACT_DIR / "skip", "w") as f:
            print("Results are in a subdirectory, not here.", file=f)

        test_config = {}

        if "hyper_parameters" not in test_config:
            test_config["hyper_parameters"] = {}

        for k, v in settings.items():
            prefix, is_hyper_param, suffix = k.partition("hyper_parameters.")
            if not is_hyper_param:
                test_config[k] = v
                continue

            test_config["hyper_parameters"][suffix] = v

        if raw_lists := test_config["hyper_parameters"].pop("raw_lists", None):
            test_config["hyper_parameters"] |= raw_lists

        skip = False
        if skip_if := test_config["hyper_parameters"].pop("skip_if", None):
            for k, v in skip_if.items():
                if test_config["hyper_parameters"].get(k) != v:
                    continue
                skip = True
                break


        failed = _run_test([None], test_config) \
            if not skip else False

    sys.exit(1 if failed else 0)


def _run_test_many_model(test_settings):
    ray_enabled = config.project.get_config("tests.fine_tuning.ray.enabled")
    fms_enabled = config.project.get_config("tests.fine_tuning.fms.enabled")
    extra = test_settings | dict(prepare_only=True, delete_other=True)

    if fms_enabled:
        run.run_toolbox_from_config("fine_tuning", "run_fine_tuning_job", extra)
    elif ray_enabled:
        run.run_toolbox_from_config("fine_tuning", "ray_fine_tuning_job", extra)

    artifact_dir = list(env.ARTIFACT_DIR.glob("*__fine_tuning__run_fine_tuning_job"))[-1]
    if fms_enabled:
        fine_tuning_job_base = artifact_dir / "src" / "pytorchjob_fine_tuning.yaml"

    elif ray_enabled:
        # fine_tuning_job_base = artifact_dir / "src" / "ray_job.yaml"
        raise NotImplemented("Ray many-model fine-tuning not implemented yet")

    if not fine_tuning_job_base.exists():
        raise FileNotFoundError(f"Something went wrong with the fine tuning job preparation. {fine_tuning_job_base} does not exist.")

    run.run_toolbox_from_config("scheduler", "generate_load", extra=dict(job_template_name=str(fine_tuning_job_base)))
