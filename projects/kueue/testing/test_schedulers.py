import sys, os
import logging
import traceback
import copy
import pathlib
import yaml
import uuid

import topsail
from topsail.testing import env, config, run, visualize, matbenchmark
import prepare

TESTING_THIS_DIR = pathlib.Path(__file__).absolute().parent

TOPSAIL_DIR = pathlib.Path(topsail.__file__).parent.parent
RUN_DIR = pathlib.Path(os.getcwd()) # for run_one_matbench
os.chdir(TOPSAIL_DIR)


def test(name=None, dry_mode=None, do_visualize=None, capture_prom=None, prepare_nodes=None):
    """
    Runs the test from the CI

    Args:
      name: name of the test to run. If empty, run all the tests of the configuration file
      dry_mode: if True, do not execute the tests, only list what would be executed
      visualize: if False, do not generate the visualization reports
      capture_prom: if False, do not capture Prometheus database
      prepare_nodes: if False, do not scale up the cluster nodes
    """

    if dry_mode is not None:
        config.ci_artifacts.set_config("tests.dry_mode", dry_mode)
    if do_visualize is not None:
        config.ci_artifacts.set_config("tests.visualize", do_visualize)
    if capture_prom is not None:
        config.ci_artifacts.set_config("tests.capture_prom", capture_prom)
    if prepare_nodes is not None:
        config.ci_artifacts.set_config("tests.schedulers.prepare_nodes", prepare_nodes)

    failed_tests = []
    tests_to_run = config.ci_artifacts.get_config("tests.schedulers.tests_to_run") \
        if not name else [name]

    for name in tests_to_run:
        with env.NextArtifactDir(f"test-case_{name}"):
            try:
                failed = _run_test_and_visualize(name)
                if failed:
                    failed_tests.append(name)
            except Exception as e:
                failed_tests.append(name)
                logging.error(f"*** Caught an exception during _run_test_and_visualize({name}): {e.__class__.__name__}: {e}")
                traceback.print_exc()

                with open(env.ARTIFACT_DIR / "FAILURE", "w") as f:
                    print(traceback.format_exc(), file=f)

                import bdb
                if isinstance(e, bdb.BdbQuit):
                    raise

            if failed_tests and config.ci_artifacts.get_config("tests.schedulers.stop_on_error"):
                logging.info("Error detected, and tests.schedulers.stop_on_error is set. Aborting.")
                break

    if failed_tests:
        with open(env.ARTIFACT_DIR / "FAILED_TESTS", "w") as f:
            print("\n".join(failed_tests), file=f)

        msg = f"Caught exception(s) in [{', '.join(failed_tests)}], aborting."
        logging.error(msg)

        raise RuntimeError(msg)



def merge(a, b, path=None):
    "updates a with b"
    if path is None: path = []
    for key in b:
        if key in a and isinstance(a[key], dict) and isinstance(b[key], dict):
            merge(a[key], b[key], path + [str(key)])
        else:
            a[key] = b[key]
    return a


def save_matbench_files(name, cfg):
    with open(env.ARTIFACT_DIR / "settings.yaml", "w") as f:
        yaml.dump(dict(scheduler_load_test=True, name=name), f)

    with open(env.ARTIFACT_DIR / "config.yaml", "w") as f:
        yaml.dump(config.ci_artifacts.config, f, indent=4)

    with open(env.ARTIFACT_DIR / "test_case_config.yaml", "w") as f:
        yaml.dump(cfg, f)

    with open(env.ARTIFACT_DIR / ".uuid", "w") as f:
        print(str(uuid.uuid4()), file=f)


def _run_test_matbenchmarking(name, test_artifact_dir_p):
    visualize.prepare_matbench()

    with env.NextArtifactDir("matbenchmarking"):
        test_artifact_dir_p[0] = env.ARTIFACT_DIR
        benchmark_values = config.ci_artifacts.get_config("tests.schedulers.test_settings")

        path_tpl = "_".join([f"{k}={{settings[{k}]}}" for k in benchmark_values.keys()]) + "_"

        expe_name = "expe"
        json_benchmark_file = matbenchmark.prepare_benchmark_file(
            path_tpl=path_tpl,
            script_tpl=f"{sys.argv[0]} matbench_run_one",
            stop_on_error=config.ci_artifacts.get_config("tests.schedulers.stop_on_error"),
            common_settings=dict(name=name),
            expe_name=expe_name,
            benchmark_values=benchmark_values,
            test_files={},
        )

        logging.info(f"Benchmark configuration to run: \n{yaml.dump(json_benchmark_file, sort_keys=False)}")

        benchmark_file, yaml_content = matbenchmark.save_benchmark_file(json_benchmark_file)

        args = matbenchmark.set_benchmark_args(benchmark_file, expe_name)

        failed = matbenchmark.run_benchmark(args)
        if failed:
            logging.error(f"_run_test_matbenchmarking: matbench benchmark failed :/")

    return failed


def _run_test(name, test_artifact_dir_p, test_override_values=None):
    dry_mode = config.ci_artifacts.get_config("tests.dry_mode")
    capture_prom = config.ci_artifacts.get_config("tests.capture_prom")
    prepare_nodes = config.ci_artifacts.get_config("tests.schedulers.prepare_nodes")

    test_templates_file = TESTING_THIS_DIR / config.ci_artifacts.get_config("tests.schedulers.test_templates_file")
    with open(test_templates_file) as f:
        test_templates = yaml.safe_load(f)

    parents_to_apply = [name]
    cfg = {"templates": []}
    while parents_to_apply:
        template_name = parents_to_apply.pop()
        cfg["templates"].insert(0, template_name)
        logging.info(f"Applying test template {template_name} ...")
        try:
            test_template = test_templates[template_name]
        except KeyError:
            logging.error(f"Test template {template_name} does not exist. Available templates: {', '.join(test_templates.keys())}")
            raise

        cfg = merge(copy.deepcopy(test_template), cfg)
        if "extends" in cfg:
            parents_to_apply += cfg["extends"]
            del cfg["extends"]

    if test_override_values:
        for key, value in test_override_values.items():
            config.set_jsonpath(cfg, key, value)

    logging.info("Test configuration: \n"+yaml.dump(cfg))

    with env.NextArtifactDir("prepare"):
        if prepare_nodes:
            prepare.prepare_test_nodes(name, cfg, dry_mode)
        else:
            logging.info("tests.schedulers.prepare_nodes=False, skipping.")

        if not dry_mode:
            if capture_prom:
                run.run_toolbox("cluster", "reset_prometheus_db", mute_stdout=True)

            run.run_toolbox_from_config("codeflare", "cleanup_appwrappers")

    with env.NextArtifactDir("scheduler_load_test"):
        test_artifact_dir_p[0] = env.ARTIFACT_DIR
        save_matbench_files(name, cfg)

        extra = {}
        failed = False
        try:
            configs = [
                ("states", "target"),
                ("states", "unexpected"),
                ("job", "template_name"),
                ("pod", "count"),
                ("pod", "runtime"),
                ("pod", "requests"),
            ]

            for (group, key) in configs:
                if not key in cfg.get(group, {}): continue
                extra[f"{group}_{key}"] = cfg[group][key]

            extra["base_name"] = name
            extra["timespan"] = cfg["timespan"]
            extra["count"] = cfg["count"]
            extra["timespan"] = cfg["timespan"]
            extra["mode"] = cfg["mode"]


            if dry_mode:
                logging.info(f"Running the load test '{name}' with {extra} ...")
                return

            try:
                run.run_toolbox_from_config("codeflare", "generate_scheduler_load", extra=extra)
            except Exception as e:
                failed = True
                msg = f"*** Caught an exception during generate_scheduler_load({name}): {e.__class__.__name__}: {e}"
                logging.error(msg)
                with open(env.ARTIFACT_DIR / "FAILURE", "w") as f:
                    print(msg)
        finally:
            with open(env.ARTIFACT_DIR / "exit_code", "w") as f:
                print("1" if failed else "0", file=f)

            if not dry_mode:
                try:
                    run.run_toolbox_from_config("codeflare", "cleanup_appwrappers", mute_stdout=True)
                except Exception as e:
                    logging.error(f"*** Caught an exception during cleanup_appwrappers({name}): {e.__class__.__name__}: {e}")
                    failed = True

                if capture_prom:
                    try:
                        run.run_toolbox("cluster", "dump_prometheus_db", mute_stdout=True)
                    except Exception as e:
                        logging.error(f"*** Caught an exception during dump_prometheus_db({name}): {e.__class__.__name__}: {e}")
                        failed = True

                # must be part of the test directory
                run.run_toolbox("cluster", "capture_environment", mute_stdout=True)
                run.run_toolbox("rhods", "capture_state", mute_stdout=True)

    logging.info(f"_run_test: Test '{name}' {'failed' if failed else 'passed'}.")

    return failed


def _run_test_and_visualize(name, test_override_values=None):
    failed = True
    do_matbenchmarking = test_override_values is None and config.ci_artifacts.get_config("tests.schedulers.matbenchmarking.enabled")
    try:
        test_artifact_dir_p = [None]
        if do_matbenchmarking:
            failed = _run_test_matbenchmarking(name, test_artifact_dir_p)
        else:
            if test_override_values is None:
                test_override_values = config.ci_artifacts.get_config("tests.schedulers.test_settings")
            failed = _run_test(name, test_artifact_dir_p, test_override_values)
    finally:
        dry_mode = config.ci_artifacts.get_config("tests.dry_mode")
        if not config.ci_artifacts.get_config("tests.visualize"):
            logging.info(f"Visualization disabled.")

        elif dry_mode:
            logging.info(f"Running in dry mode, skipping the visualization.")

        elif test_artifact_dir_p[0] is not None:
            with env.NextArtifactDir("plots"):
                visualize.prepare_matbench()

                if do_matbenchmarking:
                    visu_file = config.ci_artifacts.get_config("tests.schedulers.matbenchmarking.visu_file")
                    with config.TempValue(config.ci_artifacts, "matbench.config_file", visu_file):
                         visualize.generate_from_dir(test_artifact_dir_p[0])
                else:
                     visualize.generate_from_dir(test_artifact_dir_p[0])
        else:
            logging.warning("Not generating the visualization as the test artifact directory hasn't been created.")

    logging.info(f"_run_test_and_visualize: Test '{name}' {'failed' if failed else 'passed'}.")
    return failed


def matbench_run_one():
    with env.TempArtifactDir(RUN_DIR):
        with open(env.ARTIFACT_DIR / "settings.yaml") as f:
            settings = yaml.safe_load(f)

        with open(env.ARTIFACT_DIR / "skip", "w") as f:
            print("Results are in a subdirectory, not here.", file=f)

        name = settings.pop("name")

        failed = _run_test_and_visualize(name, settings)

    sys.exit(1 if failed else 0)
