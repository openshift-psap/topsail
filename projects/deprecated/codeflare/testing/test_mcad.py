import sys, os
import logging
import traceback
import copy
import pathlib
import yaml

from projects.core.library import env, config, run
from projects.matrix_benchmarking.library import visualize, matbenchmark

import prepare_mcad

TESTING_THIS_DIR = pathlib.Path(__file__).absolute().parent


def test(name=None, dry_mode=None, visualize=None, capture_prom=None, prepare_nodes=None):
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
    if visualize is not None:
        config.ci_artifacts.set_config("tests.visualize", visualize)
    if capture_prom is not None:
        config.ci_artifacts.set_config("tests.capture_prom", capture_prom)
    if prepare_nodes is not None:
        config.ci_artifacts.set_config("tests.mcad.prepare_nodes", prepare_nodes)

    try:
        failed_tests = []
        tests_to_run = config.ci_artifacts.get_config("tests.mcad.tests_to_run") \
            if not name else [name]

        for name in tests_to_run:
            next_count = env.next_artifact_index()
            with env.TempArtifactDir(env.ARTIFACT_DIR / f"{next_count:03d}__test-case_{name}"):
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

                if failed_tests and config.ci_artifacts.get_config("tests.mcad.stop_on_error"):
                    logging.info("Error detected, and tests.mcad.stop_on_error is set. Aborting.")
                    break

        if failed_tests:
            with open(env.ARTIFACT_DIR / "FAILED_TESTS", "w") as f:
                print("\n".join(failed_tests), file=f)

            msg = f"Caught exception(s) in [{', '.join(failed_tests)}], aborting."
            logging.error(msg)

            raise RuntimeError(msg)
    finally:
        run.run(f"testing/utils/generate_plot_index.py > {env.ARTIFACT_DIR}/report_index.html", check=False)

        if config.ci_artifacts.get_config("clusters.cleanup_on_exit"):
            cleanup_cluster()


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
        yaml.dump(dict(mcad_load_test=True, name=name), f)

    with open(env.ARTIFACT_DIR / "config.yaml", "w") as f:
        yaml.dump(config.ci_artifacts.config, f, indent=4)

    with open(env.ARTIFACT_DIR / "test_case_config.yaml", "w") as f:
        yaml.dump(cfg, f)


def _run_test_multiple_values(name, test_artifact_dir_p):
    visualize.prepare_matbench()

    next_count = env.next_artifact_index()
    with env.TempArtifactDir(env.ARTIFACT_DIR / f"{next_count:03d}__mcad_load_test_multiple_values"):
        test_artifact_dir_p[0] = env.ARTIFACT_DIR
        benchmark_values = config.ci_artifacts.get_config("tests.mcad.test_multiple_values.settings")

        path_tpl = "_".join([f"{k}={{settings[{k}]}}" for k in benchmark_values.keys()]) + "_"

        expe_name = "expe"
        json_benchmark_file = matbenchmark.prepare_benchmark_file(
            path_tpl=path_tpl,
            script_tpl=f"{sys.argv[0]} mcad_run_one_matbench",
            stop_on_error=config.ci_artifacts.get_config("tests.mcad.stop_on_error"),
            common_settings=dict(name=name),
            expe_name=expe_name,
            benchmark_values=benchmark_values
        )

        logging.info(f"Benchmark configuration to run: \n{yaml.dump(json_benchmark_file, sort_keys=False)}")

        benchmark_file = matbenchmark.save_benchmark_file(json_benchmark_file)

        args = matbenchmark.set_benchmark_args(benchmark_file, expe_name)

        failed = matbenchmark.run_benchmark(args)
        if failed:
            logging.error(f"_run_test_multiple_values: matbench benchmark failed :/")

    return failed


def _run_test(name, test_artifact_dir_p, test_override_values=None):
    dry_mode = config.ci_artifacts.get_config("tests.dry_mode")
    capture_prom = config.ci_artifacts.get_config("tests.capture_prom")
    prepare_nodes = config.ci_artifacts.get_config("tests.mcad.prepare_nodes")

    test_templates_file = TESTING_THIS_DIR / config.ci_artifacts.get_config("tests.mcad.test_templates_file")
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

    next_count = env.next_artifact_index()
    with env.TempArtifactDir(env.ARTIFACT_DIR / f"{next_count:03d}__prepare"):
        if prepare_nodes:
            prepare_mcad.prepare_test_nodes(name, cfg, dry_mode)
        else:
            logging.info("tests.mcad.prepare_nodes=False, skipping.")

        if not dry_mode:
            if capture_prom:
                run.run_toolbox("cluster", "reset_prometheus_db", mute_stdout=True)

            run.run_toolbox_from_config("codeflare", "cleanup_appwrappers")

    next_count = env.next_artifact_index()
    with env.TempArtifactDir(env.ARTIFACT_DIR / f"{next_count:03d}__mcad_load_test"):

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
                if not key in cfg["aw"].get(group, {}): continue
                extra[f"{group}_{key}"] = cfg["aw"][group][key]

            extra["aw_base_name"] = name
            extra["timespan"] = cfg["timespan"]
            extra["aw_count"] = cfg["aw"]["count"]
            extra["timespan"] = cfg["timespan"]

            job_mode = cfg["aw"]["job"].get("job_mode")

            extra["job_mode"] = bool(job_mode)

            if dry_mode:
                logging.info(f"Running the load test '{name}' with {extra} {'in Job mode' if job_mode else ''} ...")
                return

            try:
                run.run_toolbox_from_config("codeflare", "generate_mcad_load", extra=extra)
            except Exception as e:
                failed = True
                logging.error(f"*** Caught an exception during generate_mcad_load({name}): {e.__class__.__name__}: {e}")

        finally:
            with open(env.ARTIFACT_DIR / "exit_code", "w") as f:
                print("1" if failed else "0", file=f)

            if not dry_mode:
                try:
                    run.run_toolbox_from_config("codeflare", "cleanup_appwrappers")
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
                run.run_toolbox("cluster capture_environment >/dev/null")

    logging.info(f"_run_test: Test '{name}' {'failed' if failed else 'passed'}.")

    return failed


def _run_test_and_visualize(name, test_override_values=None):
    failed = True
    do_test_multiple_values = test_override_values is None and config.ci_artifacts.get_config("tests.mcad.test_multiple_values.enabled")
    try:
        test_artifact_dir_p = [None]
        if do_test_multiple_values:
            failed = _run_test_multiple_values(name, test_artifact_dir_p)
        else:
            failed = _run_test(name, test_artifact_dir_p, test_override_values)
    finally:
        dry_mode = config.ci_artifacts.get_config("tests.dry_mode")
        if not config.ci_artifacts.get_config("tests.visualize"):
            logging.info(f"Visualization disabled.")

        elif dry_mode:
            logging.info(f"Running in dry mode, skipping the visualization.")

        elif test_artifact_dir_p[0] is not None:
            next_count = env.next_artifact_index()
            with env.TempArtifactDir(env.ARTIFACT_DIR / f"{next_count:03d}__plots"):
                visualize.prepare_matbench()

                if do_test_multiple_values:
                    matbench_config_file = config.ci_artifacts.get_config("tests.mcad.test_multiple_values.matbench_config_file")
                    with config.TempValue(config.ci_artifacts, "matbench.config_file", matbench_config_file):
                         visualize.generate_from_dir(test_artifact_dir_p[0])
                else:
                     visualize.generate_from_dir(test_artifact_dir_p[0])
        else:
            logging.warning("Not generating the visualization as the test artifact directory hasn't been created.")

    logging.info(f"_run_test_and_visualize: Test '{name}' {'failed' if failed else 'passed'}.")
    return failed


def run_one_matbench():
    with open("settings.yaml") as f:
        settings = yaml.safe_load(f)

    with open("skip", "w") as f:
        print("Results are in a subdirectory, not here.", file=f)

    name = settings.pop("name")

    with env.TempArtifactDir(os.getcwd()):
        ci_artifacts_base_dir = TESTING_THIS_DIR.parent.parent
        os.chdir(ci_artifacts_base_dir)

        failed = _run_test_and_visualize(name, settings)

    sys.exit(1 if failed else 0)
