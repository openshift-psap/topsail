import math
import types
import yaml
import json
from pathlib import Path

import projects.matrix_benchmarking.visualizations.helpers.store.parsers as helpers_store_parsers


register_important_file = None  # will be when importing store/__init__.py
RUN_BENCHMARK_DIR = "*_run_metrics"

artifact_dirnames = types.SimpleNamespace()
artifact_dirnames.RUN_BENCHMARK = RUN_BENCHMARK_DIR
artifact_dirnames.CAPTURE_SYSTEM_STATE = "*__container_bench__capture_system_state"
artifact_dirnames.CAPTURE_CONTAINER_ENGINE_INFO = "*__container_bench__capture_container_engine_info"


artifact_paths = types.SimpleNamespace()  # will be dynamically populated

UNIT_MIBS = "MiB/s"
UNIT_MIBSEC = "MiB/sec"
UNIT_GBITS = "Gbits/sec"
UNIT_EVENTS = "events/sec"

BENCHMARK_TYPE_MAPPING = {
    "sysbench_cpu_benchmark": {
        "title": f"CPU ({UNIT_EVENTS})",
        "log_filename": "cpu_benchmark.log",
        "timestamp_filename": "cpu_benchmark_ts.yaml",
    },
    "sysbench_memory_read_benchmark": {
        "title": f"Memory READ ({UNIT_MIBSEC})",
        "log_filename": "memory_read_benchmark.log",
        "timestamp_filename": "memory_read_benchmark_ts.yaml",
    },
    "sysbench_memory_write_benchmark": {
        "title": f"Memory WRITE ({UNIT_MIBSEC})",
        "log_filename": "memory_write_benchmark.log",
        "timestamp_filename": "memory_write_benchmark_ts.yaml",
    },
    "sysbench_fileIO_container": {
        "title": f"File I/O Throughput ({UNIT_MIBS})",
        "log_filename": "fileIO_container.log",
        "timestamp_filename": "fileIO_container_ts.yaml",
    },
    "sysbench_fileIO_mount": {
        "title": f"File I/O Throughput ({UNIT_MIBS})",
        "log_filename": "fileIO_mount.log",
        "timestamp_filename": "fileIO_mount_ts.yaml",
    },
    "iperf_net_bridge_benchmark": {
        "title": f"Network Bitrate ({UNIT_GBITS})",
        "log_filename": "iperf_net_bridge.log",
        "timestamp_filename": "iperf_net_bridge_ts.yaml",
    },
    "iperf_net_host_benchmark": {
        "title": f"Network Bitrate ({UNIT_GBITS})",
        "log_filename": "iperf_net_host.log",
        "timestamp_filename": "iperf_net_host_ts.yaml",
    },
    "iperf_host_to_container_benchmark": {
        "title": f"Network Bitrate ({UNIT_GBITS})",
        "log_filename": "iperf_host_to_container.log",
        "timestamp_filename": "iperf_host_to_container_ts.yaml",
    },
}

IMPORTANT_FILES = [
    "config.yaml",
    ".uuid",

    f"{artifact_dirnames.RUN_BENCHMARK}/artifacts/metrics.json",

    f"{artifact_dirnames.RUN_BENCHMARK}/artifacts/cpu_benchmark.log",
    f"{artifact_dirnames.RUN_BENCHMARK}/artifacts/memory_read_benchmark.log",
    f"{artifact_dirnames.RUN_BENCHMARK}/artifacts/memory_write_benchmark.log",
    f"{artifact_dirnames.RUN_BENCHMARK}/artifacts/fileIO_container.log",
    f"{artifact_dirnames.RUN_BENCHMARK}/artifacts/fileIO_mount.log",
    f"{artifact_dirnames.RUN_BENCHMARK}/artifacts/iperf_net_bridge.log",
    f"{artifact_dirnames.RUN_BENCHMARK}/artifacts/iperf_net_host.log",
    f"{artifact_dirnames.RUN_BENCHMARK}/artifacts/iperf_host_to_container.log",

    f"{artifact_dirnames.RUN_BENCHMARK}/artifacts/cpu_benchmark_ts.yaml",
    f"{artifact_dirnames.RUN_BENCHMARK}/artifacts/memory_read_benchmark_ts.yaml",
    f"{artifact_dirnames.RUN_BENCHMARK}/artifacts/memory_write_benchmark_ts.yaml",
    f"{artifact_dirnames.RUN_BENCHMARK}/artifacts/fileIO_container_ts.yaml",
    f"{artifact_dirnames.RUN_BENCHMARK}/artifacts/fileIO_mount_ts.yaml",
    f"{artifact_dirnames.RUN_BENCHMARK}/artifacts/iperf_net_bridge_ts.yaml",
    f"{artifact_dirnames.RUN_BENCHMARK}/artifacts/iperf_net_host_ts.yaml",
    f"{artifact_dirnames.RUN_BENCHMARK}/artifacts/iperf_host_to_container_ts.yaml",

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
    if results.metrics is None:
        results.metrics = _parse_synthetic_benchmark(dirname)

    results.system_state = _parse_system_state(dirname)
    results.container_engine_info = _parse_container_engine_info(dirname)


def _parse_cpu_benchmark(line, metric):
    if "events per second:" in line:
        metric.value = float(line.split(":")[1].strip())
        metric.unit = UNIT_EVENTS
        return True
    return False


def _parse_memory_benchmark(line, metric):
    if "MiB transferred" in line:
        parts = line.split("(")
        if len(parts) >= 2:
            speed_part = parts[1].split(")")[0]
            metric.value = float(speed_part.split()[0])
            metric.unit = UNIT_MIBSEC
            return True
    return False


def _parse_fileio_benchmark(line, metric):
    if "read, MiB/s:" in line:
        metric.read_throughput = float(line.split(":")[1].strip())
        metric.unit = UNIT_MIBS
        return True
    elif "written, MiB/s:" in line:
        metric.write_throughput = float(line.split(":")[1].strip())
        metric.unit = UNIT_MIBS
        return True
    return False


def _parse_network_benchmark(line, metric):
    if "receiver" not in line:
        return False

    parts = line.split()
    if len(parts) < 7:
        return False

    for i, part in enumerate(parts):
        if "bits/sec" in part:
            try:
                bitrate_value = float(parts[i-1])
                if "Gbits/sec" in part:
                    metric.value = bitrate_value
                    metric.unit = UNIT_GBITS
                elif "Mbits/sec" in part:
                    metric.value = bitrate_value / 1000.0
                    metric.unit = UNIT_GBITS
                return True
            except (ValueError, IndexError):
                pass
    return False


BENCHMARK_PARSERS = {
    'sysbench_cpu_benchmark': _parse_cpu_benchmark,
    'sysbench_memory_read_benchmark': _parse_memory_benchmark,
    'sysbench_memory_write_benchmark': _parse_memory_benchmark,
    'sysbench_fileIO_container': _parse_fileio_benchmark,
    'sysbench_fileIO_mount': _parse_fileio_benchmark,
    'iperf_net_bridge_benchmark': _parse_network_benchmark,
    'iperf_net_host_benchmark': _parse_network_benchmark,
    'iperf_host_to_container_benchmark': _parse_network_benchmark,
}


def _read_timestamp_from_file(dirname, benchmark_path, log_file_name):
    timestamp_file = benchmark_path / "artifacts" / log_file_name.replace('.log', '_ts.yaml')
    if not timestamp_file.exists():
        return None
    try:
        with open(register_important_file(dirname, timestamp_file)) as f:
            timestamp_data = yaml.safe_load(f)
            return timestamp_data.get('start_time')
    except Exception:
        return None


@helpers_store_parsers.ignore_file_not_found
def _parse_synthetic_benchmark(dirname):
    metric = types.SimpleNamespace()
    metric.type = "synthetic_benchmark"

    if not artifact_paths.RUN_BENCHMARK:
        return None

    type_ = ""
    title_ = ""
    log_file_name = ""

    for key, config in BENCHMARK_TYPE_MAPPING.items():
        if key in dirname.name:
            type_ = key
            title_ = config['title']
            log_file_name = config['log_filename']
            break

    metric.synthetic_benchmark_type = type_
    metric.synthetic_benchmark_title = title_
    metric.timestamp = None
    metric.unit = ""
    metric.value = None

    for benchmark_path in dirname.glob(RUN_BENCHMARK_DIR):
        if not Path(benchmark_path / "artifacts" / log_file_name).exists():
            continue

        with open(
            register_important_file(dirname, benchmark_path / "artifacts" / log_file_name)
        ) as f:
            lines = f.readlines()

            parser = BENCHMARK_PARSERS.get(type_)
            if parser:
                for line in lines:
                    parser(line, metric)

            metric.full_log = "".join(lines)

        metric.timestamp = _read_timestamp_from_file(dirname, benchmark_path, log_file_name)

    return metric


@helpers_store_parsers.ignore_file_not_found
def _parse_metrics(dirname):
    metric = types.SimpleNamespace()
    metric.type = "container_bench"

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
        if not Path(benchmark_path / "artifacts" / "metrics.json").exists():
            continue
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
