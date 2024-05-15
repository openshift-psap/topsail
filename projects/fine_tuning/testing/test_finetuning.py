import sys, os
import logging
import traceback
import copy
import pathlib
import yaml
import uuid
import time
import threading

from projects.core.library import env, config, run, visualize, matbenchmark
import prepare_finetuning

TESTING_THIS_DIR = pathlib.Path(__file__).absolute().parent
TOPSAIL_DIR = pathlib.Path(config.__file__).parents[3]
RUN_DIR = pathlib.Path(os.getcwd()) # for run_one_matbench
os.chdir(TOPSAIL_DIR)


def reset_prometheus(delay=60):
    if not config.ci_artifacts.get_config("tests.capture_prom"):
        logging.info("tests.capture_prom is disabled, skipping Prometheus DB reset")
        return

    if config.ci_artifacts.get_config("tests.dry_mode"):
        logging.info("tests.dry_mode is enabled, skipping Prometheus DB reset")
        return

    with run.Parallel("cluster__reset_prometheus_dbs") as parallel:
        parallel.delayed(run.run_toolbox, "cluster", "reset_prometheus_db", mute_stdout=True)
        if config.ci_artifacts.get_config("tests.capture_prom_uwm"):
            parallel.delayed(run.run_toolbox_from_config, "cluster", "reset_prometheus_db", suffix="uwm", artifact_dir_suffix="_uwm", mute_stdout=True)

    logging.info(f"Wait {delay}s for Prometheus to restart collecting data ...")
    time.sleep(delay)


def dump_prometheus(delay=60):
    if not config.ci_artifacts.get_config("tests.capture_prom"):
        logging.info("tests.capture_prom is disabled, skipping Prometheus DB dump")
        return

    if config.ci_artifacts.get_config("tests.dry_mode"):
        logging.info("tests.dry_mode is enabled, skipping Prometheus DB dump")
        return

    logging.info(f"Wait {delay}s for Prometheus to finish collecting data ...")
    time.sleep(delay)

    with run.Parallel("cluster__dump_prometheus_dbs") as parallel:
        parallel.delayed(run.run_toolbox, "cluster", "dump_prometheus_db", mute_stdout=True)
        if config.ci_artifacts.get_config("tests.capture_prom_uwm"):
            parallel.delayed(run.run_toolbox_from_config, "cluster", "dump_prometheus_db", suffix="uwm", artifact_dir_suffix="_uwm", mute_stdout=True)


def generate_prom_results(expe_name):
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

    dump_prometheus()

    run.run_toolbox("rhods", "capture_state", run_kwargs=dict(capture_stdout=True))


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


def _run_test(test_override_values, job_index=None):
    dry_mode = config.ci_artifacts.get_config("tests.dry_mode")

    test_settings = config.ci_artifacts.get_config("tests.fine_tuning.test_settings") | test_override_values
    do_multi_model = config.ci_artifacts.get_config("tests.fine_tuning.multi_model.enabled")

    logging.info(f"Test configuration to run: \n{yaml.dump(test_settings, sort_keys=False)}")

    sources = config.ci_artifacts.get_config(f"fine_tuning.sources")
    dataset_source = sources[test_settings["dataset_name"]]

    if transform := dataset_source.get("transform", False):
        test_settings["dataset_transform"] = transform

    prepare_finetuning.prepare_namespace(test_settings)
    exit_code = 1

    if not do_multi_model:
        reset_prometheus()

    with env.NextArtifactDir("test_fine_tuning"):
        test_artifact_dir = env.ARTIFACT_DIR

        prepare_matbench_test_files(job_index)

        try:
            if dry_mode:
                logging.info("tests.dry_mode is enabled, NOT running toolbox 'fine_tuning run_toolbox_from_config'")
            else:
                run.run_toolbox_from_config("fine_tuning", "run_fine_tuning_job",
                                            extra=test_settings)
            exit_code = 0
        finally:
            with open(env.ARTIFACT_DIR / "exit_code", "w") as f:
                print(f"{exit_code}", file=f)

            exc = None
            if not do_multi_model:
                exc = run.run_and_catch(exc, dump_prometheus)

            if config.ci_artifacts.get_config("tests.capture_state"):
                exc = run.run_and_catch(exc, run.run_toolbox, "cluster", "capture_environment", mute_stdout=True)
                exc = run.run_and_catch(exc, run.run_toolbox, "rhods", "capture_state", mute_stdout=True)

            if exc:
                raise exc

    failed = False if exit_code == 0 else True

    return test_artifact_dir, failed


def _run_test_multi_model():
    if (model_name := config.ci_artifacts.get_config("tests.fine_tuning.test_settings.model_name")) is not None:
        logging.warning(f"tests.fine_tuning.test_settings.model_name should be 'null' for the multi-model test. Current value ({model_name}) ignored.")

    multi_models = config.ci_artifacts.get_config("tests.fine_tuning.multi_model.models")

    failed = False

    lock = threading.Lock()
    counter_p = [0]
    def run_in_env(job_index, model_name):
        job_name = f"job-{job_index}-{model_name}"

        with env.NextArtifactDir(f"multi_model_{model_name}", lock=lock, counter_p=counter_p):
            test_failed =_run_test(dict(model_name=model_name, name=job_name), job_index=job_index)
        if not test_failed:
            return

        with lock:
            nonlocal failed
            failed = True

    reset_prometheus()

    with env.NextArtifactDir("multi_model"):
        try:
            job_index = 0
            with run.Parallel("multi_model", dedicated_dir=False, exit_on_exception=False) as parallel:
                test_artifact_dir = env.ARTIFACT_DIR
                for model in multi_models:
                    for idx in range(model.get("replicas", 1)):
                        parallel.delayed(run_in_env, job_index, model["name"])
                        job_index += 1

        except Exception as e:
            import traceback; traceback.print_exc()

            with lock:
                failed = True
        finally:
            generate_prom_results("multi-model")

    return test_artifact_dir, failed


def _run_test_and_visualize(test_override_values=None):
    failed = True
    do_matbenchmarking = test_override_values is None and config.ci_artifacts.get_config("tests.fine_tuning.matbenchmarking.enabled")
    do_multi_model = config.ci_artifacts.get_config("tests.fine_tuning.multi_model.enabled")

    if do_matbenchmarking and do_multi_model:
        msg = "Cannot do matbenchmarking and multi-model at the same time"
        logging.error(msg)
        raise ValueError(msg)

    test_artifact_dir = None
    try:
        if do_multi_model:
            test_artifact_dir, failed = _run_test_multi_model()

        elif do_matbenchmarking:
            test_artifact_dir, failed = _run_test_matbenchmarking()

        else:
            if test_override_values is None:
                test_override_values = config.ci_artifacts.get_config("tests.fine_tuning.test_settings")
            test_artifact_dir, failed = _run_test(test_override_values)

    finally:
        dry_mode = config.ci_artifacts.get_config("tests.dry_mode")
        if not config.ci_artifacts.get_config("tests.visualize"):
            logging.info(f"Visualization disabled.")

        elif dry_mode:
            logging.info(f"Running in dry mode, skipping the visualization.")

        elif test_artifact_dir is not None:
            generate_visualization(do_matbenchmarking, test_artifact_dir)

        else:
            logging.warning("Not generating the visualization as the test artifact directory hasn't been created.")

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
    if not prom_plot_workload:
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


def _run_test_matbenchmarking():
    visualize.prepare_matbench()

    with env.NextArtifactDir("matbenchmarking"):
        test_artifact_dir = env.ARTIFACT_DIR
        benchmark_values = copy.deepcopy(config.ci_artifacts.get_config("tests.fine_tuning.test_settings"))
        remove_none_values(benchmark_values)

        test_configuration = {}
        for k in list(benchmark_values.keys()):
            v = benchmark_values[k]
            if isinstance(v, list):
                continue

            test_configuration[k] = v
            del benchmark_values[k]

        path_tpl = "_".join([f"{k}={{settings[{k}]}}" for k in benchmark_values.keys()])

        expe_name = "expe"
        json_benchmark_file = matbenchmark.prepare_benchmark_file(
            path_tpl=path_tpl,
            script_tpl=f"{sys.argv[0]} matbench_run_one",
            stop_on_error=config.ci_artifacts.get_config("tests.fine_tuning.matbenchmarking.stop_on_error"),
            common_settings=dict(),
            test_files={"test_config.yaml": test_configuration},
            expe_name=expe_name,
            benchmark_values=benchmark_values,
        )

        logging.info(f"Benchmark configuration to run: \n{yaml.dump(json_benchmark_file, sort_keys=False)}")

        benchmark_file, yaml_content = matbenchmark.save_benchmark_file(json_benchmark_file)

        args = matbenchmark.set_benchmark_args(benchmark_file, expe_name)

        failed = matbenchmark.run_benchmark(args)
        if failed:
            logging.error(f"_run_test_matbenchmarking: matbench benchmark failed :/")

    return test_artifact_dir, failed


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

        with open(env.ARTIFACT_DIR / "test_config.yaml") as f:
            test_config = yaml.safe_load(f)

        failed = _run_test_and_visualize(test_config | settings)

    sys.exit(1 if failed else 0)
