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

from projects.core.library import env, config, run, visualize, matbenchmark, merge_dicts
import prepare_finetuning

TESTING_THIS_DIR = pathlib.Path(__file__).absolute().parent
TOPSAIL_DIR = pathlib.Path(config.__file__).parents[3]
RUN_DIR = pathlib.Path(os.getcwd()) # for run_one_matbench
os.chdir(TOPSAIL_DIR)


def reset_prometheus(delay=60):
    capture_prom = config.ci_artifacts.get_config("tests.capture_prom")
    if not capture_prom:
        logging.info("tests.capture_prom is disabled, skipping Prometheus DB reset")
        return

    prom_start_ts = datetime.datetime.now()

    if capture_prom == "with-queries":
        return prom_start_ts

    if config.ci_artifacts.get_config("tests.dry_mode"):
        logging.info("tests.dry_mode is enabled, skipping Prometheus DB reset")
        return

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
            namespace = config.ci_artifacts.get_config("tests.fine_tuning.namespace"),
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

    # flag file for fine-tuning-prom visualization
    with open(anchor_file, "w") as f:
        print(expe_name, file=f)

    with open(env.ARTIFACT_DIR / ".uuid", "w") as f:
        print(str(uuid.uuid4()), file=f)

    with open(env.ARTIFACT_DIR / "config.yaml", "w") as f:
        yaml.dump(config.ci_artifacts.config, f, indent=4)

    dump_prometheus(prom_start_ts)

    if (config.ci_artifacts.get_config("tests.capture_state")
        and not config.ci_artifacts.get_config("tests.dry_mode")
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
            yaml.dump(config.ci_artifacts.config, f, indent=4)

        with open(env.ARTIFACT_DIR / ".uuid", "w") as f:
            print(str(uuid.uuid4()), file=f)


def _run_test(test_artifact_dir_p, test_override_values, job_index=None):
    dry_mode = config.ci_artifacts.get_config("tests.dry_mode")

    test_settings = config.ci_artifacts.get_config("tests.fine_tuning.test_settings") | test_override_values
    do_multi_model = config.ci_artifacts.get_config("tests.fine_tuning.multi_model.enabled")
    do_many_model = config.ci_artifacts.get_config("tests.fine_tuning.many_model.enabled")

    test_settings["hyper_parameters"] = {k: v for k, v in test_settings["hyper_parameters"].items()
                                         if v is not None}

    logging.info(f"Test configuration to run: \n{yaml.dump(test_settings, sort_keys=False)}")

    sources = config.ci_artifacts.get_config(f"fine_tuning.sources")
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
        prom_start_ts = reset_prometheus()

    with env.NextArtifactDir("test_fine_tuning"):
        test_artifact_dir_p[0] = env.ARTIFACT_DIR

        prepare_matbench_test_files(job_index)

        try:
            if dry_mode:
                logging.info(f"tests.dry_mode is enabled, NOT running with {test_settings} | {do_multi_model=} | {do_many_model=}")
            elif do_many_model:
                _run_test_many_model(test_settings)
            else:
                start_ts = _start_ts

                test_settings["model_name"] = prepare_finetuning.get_safe_model_name(test_settings["model_name"])
                run.run_toolbox_from_config("fine_tuning", "run_fine_tuning_job",
                                            extra=test_settings)
            failed = False
        finally:
            with open(env.ARTIFACT_DIR / "exit_code", "w") as f:
                print(1 if failed else 0, file=f)

            if start_ts:
                save_test_start_end(start_ts, test_settings)

            exc = None
            if not do_multi_model:
                exc = run.run_and_catch(exc, generate_prom_results, "single-model", prom_start_ts)

            if config.ci_artifacts.get_config("tests.capture_state"):
                exc = run.run_and_catch(exc, run.run_toolbox, "cluster", "capture_environment", mute_stdout=True)
                exc = run.run_and_catch(exc, run.run_toolbox, "rhods", "capture_state", mute_stdout=True)

            if exc:
                logging.warning(f"Test configuration crashed ({exc}): \n{yaml.dump(test_settings, sort_keys=False)}")

                raise exc

    if failed:
        logging.warning(f"Test configuration failed: \n{yaml.dump(test_settings, sort_keys=False)}")


    return failed


def _run_test_multi_model(test_artifact_dir_p):
    if (model_name := config.ci_artifacts.get_config("tests.fine_tuning.test_settings.model_name")) is not None:
        logging.warning(f"tests.fine_tuning.test_settings.model_name should be 'null' for the multi-model test. Current value ({model_name}) ignored.")

    multi_models = config.ci_artifacts.get_config("tests.fine_tuning.multi_model.models")

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

    prom_start_ts = reset_prometheus()

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


def _run_test_and_visualize(test_override_values=None):
    failed = True
    do_matbenchmarking = test_override_values is None and config.ci_artifacts.get_config("tests.fine_tuning.matbenchmarking.enabled")
    do_multi_model = config.ci_artifacts.get_config("tests.fine_tuning.multi_model.enabled")

    if not do_matbenchmarking and config.ci_artifacts.get_config("tests.fine_tuning.test_extra_settings"):
        msg = "Cannot use 'test_extra_settings' when 'tests.fine_tuning.tests.fine_tuning.matbenchmarking' isn't enabled."
        logging.error(msg)
        raise ValueError(msg)

    if do_matbenchmarking and do_multi_model:
        msg = "Cannot do matbenchmarking and multi-model at the same time"
        logging.error(msg)
        raise ValueError(msg)

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
                test_override_values = config.ci_artifacts.get_config("tests.fine_tuning.test_settings")
            failed = _run_test(test_artifact_dir_p, test_override_values)

    finally:
        dry_mode = config.ci_artifacts.get_config("tests.dry_mode")
        if not config.ci_artifacts.get_config("tests.visualize"):
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
        visualize.prepare_matbench()

        if do_matbenchmarking:
            visu_file = config.ci_artifacts.get_config("tests.fine_tuning.matbenchmarking.visu_file")
            with config.TempValue(config.ci_artifacts, "matbench.config_file", visu_file):
                exc = run.run_and_catch(exc, visualize.generate_from_dir, test_artifact_dir)

        else:
            exc = run.run_and_catch(exc, visualize.generate_from_dir, test_artifact_dir)

    prom_plot_workload = config.ci_artifacts.get_config("tests.prom_plot_workload")
    capture_prom = config.ci_artifacts.get_config("tests.capture_prom")

    if not prom_plot_workload or not capture_prom:
        if not capture_prom:
            logging.info(f"Setting tests.capture_prom is disabled, skipping Prometheus visualization.")
        else:
            logging.info(f"Setting tests.prom_plot_workload isn't set, nothing else to generate.")

        if exc:
            raise exc

        return

    with (
            env.NextArtifactDir("prom_plots"),
            config.TempValue(config.ci_artifacts, "matbench.workload", prom_plot_workload)
    ):
        logging.info(f"Generating the plots with workload={prom_plot_workload}")

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
        config.ci_artifacts.set_config("tests.dry_mode", dry_mode)
    if do_visualize is not None:
        config.ci_artifacts.set_config("tests.visualize", do_visualize)
    if capture_prom is not None:
        config.ci_artifacts.set_config("tests.capture_prom", capture_prom)

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
    visualize.prepare_matbench()

    with env.NextArtifactDir("matbenchmarking"):
        test_settings = config.ci_artifacts.get_config("tests.fine_tuning.test_settings")
        test_artifact_dir_p[0] = env.ARTIFACT_DIR

        test_extra_settings_lst = config.ci_artifacts.get_config("tests.fine_tuning.test_extra_settings")
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

            expe_to_run[expe_name] = benchmark_values

        path_tpl = "{settings[name]}"

        json_benchmark_file = matbenchmark.prepare_benchmark_file(
            path_tpl=path_tpl,
            script_tpl=f"{sys.argv[0]} matbench_run_one",
            stop_on_error=config.ci_artifacts.get_config("tests.fine_tuning.matbenchmarking.stop_on_error"),
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

        failed = _run_test([None], test_config)

    sys.exit(1 if failed else 0)


def _run_test_many_model(test_settings):
    run.run_toolbox_from_config("fine_tuning", "run_fine_tuning_job",
                                extra=test_settings | dict(prepare_only=True, delete_other=True))
    artifact_dir = list(env.ARTIFACT_DIR.glob("*__fine_tuning__run_fine_tuning_job"))[-1]

    fine_tuning_job_base = artifact_dir / "src" / "pytorchjob_fine_tuning.yaml"
    if not fine_tuning_job_base.exists():
        raise FileNotFoundError(f"Something went wrong with the fine tuning job preparation. {fine_tuning_job_base} does not exist.")

    run.run_toolbox_from_config("scheduler", "generate_load", extra=dict(job_template_name=str(fine_tuning_job_base)))
