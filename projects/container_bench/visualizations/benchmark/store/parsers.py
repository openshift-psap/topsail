import math
import types
import yaml
import json

import projects.matrix_benchmarking.visualizations.helpers.store.parsers as helpers_store_parsers


register_important_file = None  # will be when importing store/__init__.py
RUN_BENCHMARK_DIR = "*_run_metrics"

artifact_dirnames = types.SimpleNamespace()
artifact_dirnames.RUN_BENCHMARK = RUN_BENCHMARK_DIR
artifact_dirnames.CAPTURE_SYSTEM_STATE = "*__container_bench__capture_system_state"
artifact_dirnames.CAPTURE_CONTAINER_ENGINE_INFO = "*__container_bench__capture_container_engine_info"


artifact_paths = types.SimpleNamespace()  # will be dynamically populated

IMPORTANT_FILES = [
    "config.yaml",
    ".uuid",

    f"{artifact_dirnames.RUN_BENCHMARK}/artifacts/metrics.json",

    f"{artifact_dirnames.CAPTURE_SYSTEM_STATE}/artifacts/system_info.txt",
    f"{artifact_dirnames.CAPTURE_CONTAINER_ENGINE_INFO}/artifacts/container_engine_info.json",
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
    memory_usages = []
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
            memory_usages.append(d.get("memory_usage", []))

    if not execution_times:
        return None

    metric.cpu = [_calculate_usage_metric(cpu) for cpu in zip(*cpu_usages)]
    metric.execution_time_95th_percentile = _calculate_percentile(execution_times, 95)
    metric.execution_time_jitter = _calculate_jitter(execution_times)
    metric.memory = [_calculate_usage_metric(memory) for memory in zip(*memory_usages)]

    network_send = [
        _calculate_usage_metric(send) for send in zip(*network_send_usages)
    ]
    network_recv = [
        _calculate_usage_metric(recv) for recv in zip(*network_recv_usages)
    ]
    metric.network = dict(send=network_send, recv=network_recv)

    disk_read = [
        _calculate_usage_metric(read) for read in zip(*disk_read_usages)
    ]
    disk_write = [
        _calculate_usage_metric(write) for write in zip(*disk_write_usages)
    ]
    metric.disk = dict(read=disk_read, write=disk_write)
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
        register_important_file(dirname, artifact_paths.CAPTURE_SYSTEM_STATE / "artifacts" / "system_info.txt")
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
            artifact_paths.CAPTURE_CONTAINER_ENGINE_INFO / "artifacts" / "container_engine_info.json"
        )
    ) as f:
        container_engine_info = json.load(f)
    return container_engine_info


def _calculate_usage_metric(data):
    if data is None or len(data) == 0:
        return None
    return types.SimpleNamespace(
        percentile_75th=_calculate_percentile(data, 75),
        percentile_50th=_calculate_percentile(data, 50),
        percentile_25th=_calculate_percentile(data, 25),
    )


def _calculate_percentile(data, percentile=95):
    if data is None or len(data) == 0:
        return None

    sorted_values = sorted(data)
    n = len(sorted_values)

    rank = (percentile / 100) * (n - 1)

    if rank.is_integer():
        return sorted_values[int(rank)]
    lower_index = math.floor(rank)
    upper_index = math.ceil(rank)
    fraction = rank - lower_index

    lower_value = sorted_values[lower_index]
    upper_value = sorted_values[upper_index]

    return lower_value + fraction * (upper_value - lower_value)


def _calculate_jitter(data):
    if data is None or len(data) < 2:
        return None
    differences = [abs(data[i] - data[i-1]) for i in range(1, len(data))]
    return sum(differences) / len(differences)
