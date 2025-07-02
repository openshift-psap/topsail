import types
import yaml
import json

import projects.matrix_benchmarking.visualizations.helpers.store.parsers as helpers_store_parsers


register_important_file = None  # will be when importing store/__init__.py
RUN_BENCHMARK_DIR = "*_run_metrics"

artifact_dirnames = types.SimpleNamespace()
artifact_dirnames.TEST_RUN_DIR = "*_run_dir"
artifact_dirnames.RUN_BENCHMARK = RUN_BENCHMARK_DIR
artifact_dirnames.CAPTURE_SYSTEM_STATE = "*__container_bench__capture_system_state"
artifact_dirnames.CAPTURE_CONTAINER_ENGINE_INFO = "*__container_bench__capture_container_engine_info"


artifact_paths = types.SimpleNamespace()  # will be dynamically populated

IMPORTANT_FILES = [
    "config.yaml",
    ".uuid",

    f"{artifact_dirnames.TEST_RUN_DIR}/output/output.json",
    f"{artifact_dirnames.TEST_RUN_DIR}/src/benchmark.config.yaml",

    f"{artifact_dirnames.RUN_BENCHMARK}/artifacts/metrics.json",

    f"{artifact_dirnames.CAPTURE_SYSTEM_STATE}/artifacts/system_profiler.txt",
    f"{artifact_dirnames.CAPTURE_CONTAINER_ENGINE_INFO}/artifacts/container_engine_info.txt",
]


def parse_always(results, dirname, import_settings):
    # parsed even when reloading from the cache file

    results.from_local_env = helpers_store_parsers.parse_local_env(dirname)


def parse_once(results, dirname):
    results.test_config = helpers_store_parsers.parse_test_config(dirname)

    results.test_uuid = helpers_store_parsers.parse_test_uuid(dirname)
    capture_state_dir = artifact_paths.CAPTURE_SYSTEM_STATE

    results.from_env = helpers_store_parsers.parse_env(dirname, results.test_config, capture_state_dir)

    results.metrics = _parse_metrics(dirname)

    results.system_state = _parse_system_state(dirname)
    results.container_engine_info = _parse_container_engine_info(dirname)


@helpers_store_parsers.ignore_file_not_found
def _parse_metrics(dirname):
    metric = types.SimpleNamespace()

    if not artifact_paths.RUN_BENCHMARK:
        return None

    network_send_usages = []
    network_recv_usages = []
    disk_read_usages = []
    disk_write_usages = []
    cpu_usages = []
    execution_times = []
    interval = 0
    command = ""
    timestamp = 0
    power_usages = []
    for benchmark_path in dirname.glob(RUN_BENCHMARK_DIR):
        with open(
            register_important_file(dirname, benchmark_path / "artifacts" / "metrics.json")
        ) as f:
            d = json.load(f)
            interval = d.get("interval", 0.5)
            command = d.get("command", "")
            timestamp = d.get("timestamp", 0)

            network_send_usages.append(d.get("network_usage", {}).get("send", []))
            network_recv_usages.append(d.get("network_usage", {}).get("recv", []))

            disk_read_usages.append(d.get("disk_usage", {}).get("read", []))
            disk_write_usages.append(d.get("disk_usage", {}).get("write", []))

            cpu_usages.append(d.get("cpu_usage", []))
            execution_times.append(d.get("execution_time", 0.0))
            power_usages.append(d.get("power_usage", []))

    if not execution_times:
        return None

    metric.cpu = [sum(cpu) / len(cpu) for cpu in zip(*cpu_usages)]
    metric.execution_time = sum(execution_times) / len(execution_times)
    metric.power = [sum(power) / len(power) for power in zip(*power_usages)]

    network_send_avg = [sum(send) / len(send) for send in zip(*network_send_usages)]
    network_recv_avg = [sum(recv) / len(recv) for recv in zip(*network_recv_usages)]
    metric.network = dict(send=network_send_avg, recv=network_recv_avg)

    disk_read_avg = [sum(read) / len(read) for read in zip(*disk_read_usages)]
    disk_write_avg = [sum(write) / len(write) for write in zip(*disk_write_usages)]
    metric.disk = dict(read=disk_read_avg, write=disk_write_avg)
    metric.interval = interval

    metric.command = command
    metric.timestamp = timestamp
    return metric


@helpers_store_parsers.ignore_file_not_found
def _parse_system_state(dirname):
    system_state = types.SimpleNamespace()
    if not artifact_paths.CAPTURE_SYSTEM_STATE:
        return None

    with open(
        register_important_file(dirname, artifact_paths.CAPTURE_SYSTEM_STATE / "artifacts" / "system_profiler.txt")
    ) as f:
        system_state = yaml.safe_load(f)
    return system_state


@helpers_store_parsers.ignore_file_not_found
def _parse_container_engine_info(dirname):
    container_engine_info = types.SimpleNamespace()
    if not artifact_paths.CAPTURE_CONTAINER_ENGINE_INFO:
        return None

    with open(
        register_important_file(
            dirname,
            artifact_paths.CAPTURE_CONTAINER_ENGINE_INFO / "artifacts" / "container_engine_info.txt"
        )
    ) as f:
        container_engine_info = yaml.safe_load(f)
    return container_engine_info
