import types
import pathlib
import logging
import yaml
import os
import json
import datetime
from collections import defaultdict

import jsonpath_ng

import matrix_benchmarking.cli_args as cli_args
import matrix_benchmarking.store.prom_db as store_prom_db

from . import prom as workload_prom


register_important_file = None # will be when importing store/__init__.py

K8S_TIME_FMT = "%Y-%m-%dT%H:%M:%SZ"
SHELL_DATE_TIME_FMT = "%a %b %d %H:%M:%S %Z %Y"
ANSIBLE_LOG_DATE_TIME_FMT = "%Y-%m-%d %H:%M:%S"

artifact_dirnames = types.SimpleNamespace()
artifact_dirnames.LLM_LOAD_TEST_RUN_DIR = "*__llm_load_test__run"

IMPORTANT_FILES = [
    "config.yaml",

    f"{artifact_dirnames.LLM_LOAD_TEST_RUN_DIR}/output/ghz-multiplexed-results*.json",
]

def ignore_file_not_found(fn):
    def decorator(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except FileNotFoundError as e:
            logging.warning(f"{fn.__name__}: FileNotFoundError: {e}")
            return None

    return decorator


def _parse_always(results, dirname, import_settings):
    # parsed even when reloading from the cache file

    results.from_local_env = _parse_local_env(dirname)
    results.test_config = _parse_test_config(dirname)


def _parse_once(results, dirname):
    results.llm_load_test_output = _parse_llm_load_test_output(dirname)
    results.predictor_logs = _parse_predictor_logs(dirname)
    results.test_start_end = _parse_test_start_end(dirname, results.llm_load_test_output)

def _parse_local_env(dirname):
    from_local_env = types.SimpleNamespace()

    from_local_env.artifacts_basedir = None
    from_local_env.source_url = None
    from_local_env.is_interactive = False

    try:
        with open(dirname / "source_url") as f: # not an important file
            from_local_env.source_url = f.read().strip()
            from_local_env.artifacts_basedir = pathlib.Path(urllib.parse.urlparse(from_local_env.source_url).path)
    except FileNotFoundError as e:
        pass

    logging.debug(f"Source_url: {from_local_env.source_url}, artifacts_basedir: {from_local_env.artifacts_basedir}")

    if not cli_args.kwargs.get("generate"):
        # running in interactive mode
        from_local_env.is_interactive = True
        from_local_env.artifacts_basedir = dirname
        return from_local_env

    # running in generate mode

    # This must be parsed from the process env (not the file), to
    # properly generate the error report links to the image.
    job_name = os.getenv("JOB_NAME_SAFE", "")

    if job_name.endswith("-plot"):
        # running independently of the test, the source_url file must be available
        if from_local_env.source_url is None:
            logging.warning(f"The source URL should be available when running from '{job_name}'")
            from_local_env.source_url = "/missing/source/url"
            from_local_env.artifacts_basedir = dirname

    elif "ARTIFACT_DIR" in os.environ:

        # os.path.relpath can return '..', but pathlib.Path().relative_to cannot
        from_local_env.source_url = pathlib.Path(os.path.relpath(dirname,
                                                                 pathlib.Path(os.environ["ARTIFACT_DIR"])))
        from_local_env.artifacts_basedir = from_local_env.source_url

    else:
        logging.warning(f"Unknown execution environment: JOB_NAME_SAFE={job_name} ARTIFACT_DIR={os.environ.get('ARTIFACT_DIR')}")
        from_local_env.artifacts_basedir = dirname.absolute()

    return from_local_env


def _parse_test_config(dirname):
    test_config = types.SimpleNamespace()

    filename = pathlib.Path("config.yaml")
    test_config.filepath = dirname / filename

    with open(register_important_file(dirname, filename)) as f:
        yaml_file = test_config.yaml_file = yaml.safe_load(f)

    if not yaml_file:
        logging.error(f"Config file '{filename}' is empty ...")
        yaml_file = test_config.yaml_file = {}

    def get(key, missing=...):
        nonlocal yaml_file
        jsonpath_expression = jsonpath_ng.parse(f'$.{key}')

        match = jsonpath_expression.find(yaml_file)
        if not match:
            if missing != ...:
                return missing

            raise KeyError(f"Key '{key}' not found in {filename} ...")

        return match[0].value

    test_config.get = get

    return test_config


@ignore_file_not_found
def _parse_llm_load_test_output(dirname):
    llm_load_test_output = []
    for llm_output_file in (dirname / artifact_paths.LLM_LOAD_TEST_RUN_DIR / "output").glob("ghz-multiplexed-results-*.json"):
        register_important_file(dirname, llm_output_file.relative_to(dirname))

        with open(llm_output_file) as f:
            llm_data = json.load(f)

        llm_load_test_output += llm_data

    return llm_load_test_output


@ignore_file_not_found
def _parse_predictor_logs(dirname):
    capture_state_dirs = list(dirname.glob("*__watsonx_serving__capture_state/"))

    if not capture_state_dirs:
        logging.error("No 'watsonx_serving__capture_state' directory found in {dirname} ...")
        return

    predictor_logs = types.SimpleNamespace()
    predictor_logs.distribution = defaultdict(int)
    predictor_logs.line_count = 0
    last_capture_state_dir = capture_state_dirs[-1] # ignore the capture done after the deployment

    for log_file in last_capture_state_dir.glob("logs/*.log"):

        for line in open(log_file).readlines():
            predictor_logs.line_count += 1

            if '"severity":"ERROR"' in line:
                predictor_logs.distribution["errors"] += 1
            if '"channel": "DESTROY-THRD"' in line:
                predictor_logs.distribution["DESTROY-THRD"] += 1
            if '"channel": "ABORT-ACTION"' in line:
                predictor_logs.distribution["ABORT-ACTION"] += 1

    return predictor_logs


def _parse_test_start_end(dirname, llm_load_test_output):
    test_start_end = types.SimpleNamespace()
    test_start_end.start = None
    test_start_end.end = None

    for entry in llm_load_test_output:
        start = entry["details"][0]["timestamp"]
        if test_start_end.start is None or start < test_start_end.start:
            test_start_end.start = start

        end = entry["date"]
        if test_start_end.end is None or end > test_start_end.end:
            test_start_end.end = end

    return test_start_end
