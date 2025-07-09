import types
import yaml
import json
import dateutil.parser

import projects.matrix_benchmarking.visualizations.helpers.store.parsers as helpers_store_parsers

from pathlib import Path

register_important_file = None  # will be when importing store/__init__.py

artifact_dirnames = types.SimpleNamespace()
artifact_dirnames.TEST_RUN_DIR = "*_run_dir"
artifact_dirnames.POWER_USAGE_CPU = "*__container_benchmark__capture_power_usage_cpu_power"
artifact_dirnames.RUN_BENCHMARK = "*_run_metrics"
artifact_dirnames.CAPTURE_SYSTEM_STATE = "*__container_bench__capture_system_state"
artifact_dirnames.CAPTURE_CONTAINER_ENGINE_INFO = "*__container_bench__capture_container_engine_info"


artifact_paths = types.SimpleNamespace()  # will be dynamically populated

IMPORTANT_FILES = [
    "config.yaml",
    ".uuid",

    f"{artifact_dirnames.TEST_RUN_DIR}/output/output.json",
    f"{artifact_dirnames.TEST_RUN_DIR}/src/benchmark.config.yaml",

    f"{artifact_dirnames.POWER_USAGE_CPU}/artifacts/power_usage.txt",
    f"{artifact_dirnames.RUN_BENCHMARK}/artifacts/metrics.log",

    f"{artifact_dirnames.CAPTURE_SYSTEM_STATE}/artifacts/system_profiler.txt",
    f"{artifact_dirnames.CAPTURE_CONTAINER_ENGINE_INFO}/artifacts/container_engine_info.txt",
]


def parse_always(results, dirname, import_settings):
    # parsed even when reloading from the cache file

    results.from_local_env = helpers_store_parsers.parse_local_env(dirname)


def parse_once(results, dirname):
    results.test_config = helpers_store_parsers.parse_test_config(dirname)

    results.test_uuid = helpers_store_parsers.parse_test_uuid(dirname)
    capture_state_dir = artifact_paths.TEST_RUN_DIR

    results.from_env = helpers_store_parsers.parse_env(dirname, results.test_config, capture_state_dir)

    results.cpu_power_usage = _parse_cpu_power_metrics(dirname)
    results.metrics = _parse_metrics(dirname)

    results.system_state = _parse_system_state(dirname)
    results.container_engine_info = _parse_container_engine_info(dirname)
    print(f"Parsed results: {results}")


@helpers_store_parsers.ignore_file_not_found
def _parse_cpu_power_metrics(dirname):
    cpu_power_usage = types.SimpleNamespace()
    cpu_power_usage.machine = None
    cpu_power_usage.os = None
    cpu_power_usage.usage = []

    current_ts = None
    current_entry = None

    if not artifact_paths.POWER_USAGE_CPU:
        return None

    with open(
        register_important_file(dirname, artifact_paths.POWER_USAGE_CPU / "artifacts" / "power_usage.txt")
    ) as f:
        for line in f.readlines():
            key, is_kv, value = line.partition(":")
            key = key.strip()
            value = value.strip()

            if key == "Machine model":
                cpu_power_usage.machine = line.partition(":")[2].strip()
            elif key == "OS version":
                cpu_power_usage.os = line.partition(":")[2].strip()
            elif key.startswith("*** Sampled system activity"):
                current_ts_str = line.partition("(")[2].partition(")")[0]
                current_ts = dateutil.parser.parse(current_ts_str)
                pass
            elif key == "**** Processor usage ****":
                cpu_power_usage.usage.append(types.SimpleNamespace())
                current_entry = cpu_power_usage.usage[-1]
                current_entry.ts = current_ts

            if not current_entry:
                continue  # incomplete ...

            if key == "CPU Power":
                current_entry.power_mw = float(value.replace(" mW", ""))
                current_entry.complete = True

    if cpu_power_usage.usage and "complete" not in cpu_power_usage.usage[-1].__dict__:
        cpu_power_usage.usage.pop()

    return cpu_power_usage


@helpers_store_parsers.ignore_file_not_found
def _parse_metrics(dirname):
    metric = types.SimpleNamespace()

    if not artifact_paths.RUN_BENCHMARK:
        return None

    with open(
        register_important_file(dirname, artifact_paths.RUN_BENCHMARK / "artifacts" / "metrics.json")
    ) as f:
        d = json.load(f)
        metric.network = d.get("network_usage", [])
        metric.disk = d.get("disk_usage", [])
        metric.cpu = d.get("overall_cpu_usage", [])
        metric.execution_time = d.get("execution_time", 0.0)
        metric.interval = d.get("interval", 0.5)

    return metric


def _parse_system_state(dirname):
    system_state = types.SimpleNamespace()
    if not artifact_paths.CAPTURE_SYSTEM_STATE:
        return None

    with open(
        register_important_file(dirname, artifact_paths.CAPTURE_SYSTEM_STATE / "artifacts" / "system_profiler.txt")
    ) as f:
        system_state = yaml.safe_load(f)

    return system_state


def _parse_container_engine_info(dirname):
    system_state = types.SimpleNamespace()
    if not artifact_paths.CAPTURE_CONTAINER_ENGINE_INFO:
        return None

    with open(
        register_important_file(
            dirname,
            artifact_paths.CAPTURE_CONTAINER_ENGINE_INFO / "artifacts" / "container_engine_info.txt"
        )
    ) as f:
        system_state = yaml.safe_load(f)

    return system_state
