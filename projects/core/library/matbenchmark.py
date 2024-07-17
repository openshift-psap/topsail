import os
import logging
import functools
import yaml
import json

from . import env, config, run


def _json_dumper(obj, strict=False):
    import datetime
    import pathlib

    if hasattr(obj, "toJSON"):
        return obj.toJSON()

    elif hasattr(obj, "json"):
        return obj.dict(by_alias=True)

    elif hasattr(obj, "__dict__"):
        return obj.__dict__

    if isinstance(obj, datetime.datetime):
        return obj.isoformat()

    elif isinstance(obj, pathlib.Path):
        return str(obj)
    elif not strict:
        return str(obj)
    else:
        raise RuntimeError(f"No default serializer for object of type {obj.__class__}: {obj}")


def prepare_benchmark_file(
        path_tpl:str,
        script_tpl:str,
        stop_on_error:bool,
        common_settings:dict,
        test_files:dict,
        expe_name:str = None,
        benchmark_values:dict = None,
        expe_to_run: dict = None,
):

    json_benchmark_file = {}
    json_benchmark_file["--path_tpl"] = path_tpl
    json_benchmark_file["--script_tpl"] = script_tpl
    json_benchmark_file["--remote_mode"] = False
    json_benchmark_file["--stop_on_error"] = stop_on_error
    json_benchmark_file["test_files"] = test_files
    json_benchmark_file["common_settings"] = common_settings
    if expe_to_run:
        json_benchmark_file["--expe_to_run"] = list(expe_to_run.keys())
        json_benchmark_file["expe"] = expe_to_run
    else:
        json_benchmark_file["--expe_to_run"] = [expe_name]
        json_benchmark_file[expe_name] = expe = {}
        expe[expe_name] = benchmark_values

    return json_benchmark_file


def save_benchmark_file(benchmark_file_content, dirname=None, name="benchmark.yaml"):
    if dirname is None:
        dirname = env.ARTIFACT_DIR

    benchmark_file = dirname / name

    logging.info(f"Saving MatrixBenchmarking benchmark file into {benchmark_file} ...")
    # properly convert all the field to string
    benchmark_file_safe_content = json.loads(json.dumps(benchmark_file_content, default=functools.partial(_json_dumper, strict=False)))

    yaml_content = yaml.dump(benchmark_file_safe_content, default_flow_style=False, sort_keys=False, width=1000)
    with open(benchmark_file, "w") as f:
        print(yaml_content, file=f)

    return benchmark_file, yaml_content


def set_benchmark_args(benchmark_file, expe_name=None, results_dirname=None):
    if results_dirname is None:
        results_dirname = benchmark_file.parent

    args = {}

    args["--workload"] = config.ci_artifacts.get_config("matbench.workload")
    args["--benchmark_file"] = str(benchmark_file)
    args["--results_dirname"] = str(results_dirname)
    if expe_name:
        args["--expe_to_run"] = expe_name

    return args


def run_benchmark(args, dry_run=False):
    logging.info(f"Running MatrixBenchmarking rehearsal with '{args['--benchmark_file']}'...")

    BENCHMARK_CMD_BASE = "matbench benchmark"
    cmd_args = " ".join([f"{k}={v}" for k, v in args.items()])
    cmd = f"CI_ARTIFACTS_FROM_CONFIG_FILE={config.ci_artifacts.config_path} {BENCHMARK_CMD_BASE} {cmd_args}"

    with open(env.ARTIFACT_DIR / "benchmark.cmd", "w") as f:
        print(cmd, file =f)

    rehearsal_log_file = env.ARTIFACT_DIR / "benchmark-rehearsal.log"
    test_log_file = env.ARTIFACT_DIR / "benchmark.log"
    try:
        run.run(f"{cmd} 1>'{rehearsal_log_file}' 2>&1")
        logging.info("Rehearsal done.")
    except Exception as e:
        logging.error(f"MatrixBenchmark benchmark rehearsal failed. See '{rehearsal_log_file}' for further detals.")
        return True # failed

    if dry_run:
        logging.info("Dry-run enabled, skipping the benchmark execution.")
        return

    try:
        run.run(f"{cmd} --run 2>&1 | tee -a '{test_log_file}'")
        logging.info("Benchmark done.")
    except Exception as e:
        msg = f"MatrixBenchmark benchmark failed."
        logging.error(msg)
        with open(env.ARTIFACT_DIR / "FAILURE", "w") as f:
            print(msg, file=f)

        return True # failed

    return False # didn't fail
