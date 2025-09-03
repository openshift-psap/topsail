import types
import pathlib
import logging
import yaml
import os
import json
import datetime
from collections import defaultdict
import dateutil.parser
import urllib.parse
import uuid

import matrix_benchmarking.cli_args as cli_args

import projects.matrix_benchmarking.visualizations.helpers.store as helpers_store
import projects.matrix_benchmarking.visualizations.helpers.store.parsers as helpers_store_parsers

from . import lts_parser

register_important_file = None # will be when importing store/__init__.py

artifact_dirnames = types.SimpleNamespace()
artifact_dirnames.LLM_LOAD_TEST_RUN_DIR = "*__llm_load_test__run"
artifact_dirnames.MAC_AI_POWER_USAGE_GPU = "*__mac_ai__remote_capture_power_usage_gpu_power"
artifact_dirnames.MAC_AI_CPU_RAM_USAGE = "*__mac_ai__remote_capture_cpu_ram_usage"
artifact_dirnames.MAC_AI_VIRTGPU_MEMORY = "*__mac_ai__remote_capture_virtgpu_memory"
artifact_dirnames.MAC_AI_REMOTE_LLAMA_CPP_RUN_MODEL = "*__mac_ai__remote_llama_cpp_run_model"
artifact_dirnames.MAC_AI_REMOTE_LLAMA_CPP_RUN_BENCH = "*__mac_ai__remote_llama_cpp_run_bench"
artifact_dirnames.MAC_AI_REMOTE_RAMALAMA_RUN_BENCH = "*__mac_ai__remote_ramalama_run_bench"
artifact_dirnames.LIGHTSPEED_RUN_BENCH = "*__lightspeed_run_bench"
artifact_dirnames.LIGHTSPEED_START_SERVER = "*__lightspeed_start_server"
artifact_dirnames.MAC_AI_REMOTE_CAPTURE_SYSTEM_STATE = "*__mac_ai__remote_capture_system_state"

artifact_paths = types.SimpleNamespace() # will be dynamically populated

IMPORTANT_FILES = [
    "config.yaml",
    ".uuid",

    "ramalama-commit.info",

    f"{artifact_dirnames.LLM_LOAD_TEST_RUN_DIR}/output/output.json",
    f"{artifact_dirnames.LLM_LOAD_TEST_RUN_DIR}/src/llm_load_test.config.yaml",

    f"{artifact_dirnames.MAC_AI_POWER_USAGE_GPU}/artifacts/power_usage.txt",
    f"{artifact_dirnames.MAC_AI_CPU_RAM_USAGE}/artifacts/cpu_ram_usage.txt",
    f"{artifact_dirnames.MAC_AI_VIRTGPU_MEMORY}/artifacts/memory.txt",

    f"{artifact_dirnames.MAC_AI_REMOTE_LLAMA_CPP_RUN_MODEL}/artifacts/build.*.log",
    f"{artifact_dirnames.MAC_AI_REMOTE_RAMALAMA_RUN_BENCH}/artifacts/llama-bench.log",

    f"{artifact_dirnames.MAC_AI_REMOTE_LLAMA_CPP_RUN_BENCH}/artifacts/llama-bench.log",
    f"{artifact_dirnames.MAC_AI_REMOTE_LLAMA_CPP_RUN_BENCH}/artifacts/test-backend-ops_perf.log",

    f"{artifact_dirnames.LIGHTSPEED_RUN_BENCH}/artifacts/llama-bench.log",
    f"{artifact_dirnames.LIGHTSPEED_START_SERVER}/inspect-image.json",

    f"{artifact_dirnames.MAC_AI_REMOTE_CAPTURE_SYSTEM_STATE}/artifacts/system_profiler.txt",
]


def parse_always(results, dirname, import_settings):
    # parsed even when reloading from the cache file

    results.from_local_env = helpers_store_parsers.parse_local_env(dirname)


def parse_once(results, dirname):
    results.test_config = helpers_store_parsers.parse_test_config(dirname)

    results.test_uuid = helpers_store_parsers.parse_test_uuid(dirname)
    capture_state_dir = artifact_paths.LLM_LOAD_TEST_RUN_DIR

    results.from_env = helpers_store_parsers.parse_env(dirname, results.test_config, capture_state_dir)

    results.llm_load_test_config = _parse_llm_load_test_config(dirname)
    results.llm_load_test_output = _parse_llm_load_test_output(dirname)
    results.gpu_power_usage = _parse_gpu_power_metrics(dirname)
    results.cpu_ram_usage = _parse_cpu_ram_metrics(dirname)
    results.virtgpu_metrics = _parse_virtgpu_memory_metrics(dirname)
    results.file_links = _parse_file_links(dirname)

    results.llama_bench_results = _parse_llama_bench_results(dirname)
    results.llama_micro_bench_results = _parse_llama_micro_bench_results(dirname)

    results.test_start_end = _parse_test_start_end(dirname, results.llm_load_test_output)

    results.system_state = _parse_system_state(dirname)

    results.ramalama_commit_info = _parse_ramalama_commit_info(dirname)

    results.lightspeed_info = _parse_lightspeed_info(dirname)


def _parse_file_links(dirname):
    file_links = types.SimpleNamespace()
    if not  artifact_paths.MAC_AI_REMOTE_LLAMA_CPP_RUN_MODEL:
        return None

    server_logs = dirname / artifact_paths.MAC_AI_REMOTE_LLAMA_CPP_RUN_MODEL / "artifacts" / "llama_cpp.log"

    file_links.server_logs = server_logs.relative_to(dirname) \
        if server_logs.exists() else None

    file_links.server_build_logs = {}
    for f in (dirname / artifact_paths.MAC_AI_REMOTE_LLAMA_CPP_RUN_MODEL / "artifacts").glob("build.*.log"):
        file_links.server_build_logs[f.name] = f.relative_to(dirname)

    return file_links


@helpers_store_parsers.ignore_file_not_found
def _parse_gpu_power_metrics(dirname):
    gpu_power_usage = types.SimpleNamespace()
    gpu_power_usage.machine = None
    gpu_power_usage.os = None
    gpu_power_usage.usage = []

    current_ts = None
    current_entry = None

    if not artifact_paths.MAC_AI_POWER_USAGE_GPU:
        return None

    with open(register_important_file(dirname, artifact_paths.MAC_AI_POWER_USAGE_GPU / "artifacts" / "power_usage.txt")) as f:

        for line in f.readlines():
            key, is_kv, value = line.partition(":")
            key = key.strip()
            value = value.strip()

            if key == "Machine model":
                gpu_power_usage.machine = line.partition(":")[2].strip()
            elif key == "OS version":
                gpu_power_usage.os = line.partition(":")[2].strip()
            elif key.startswith("*** Sampled system activity"):
                current_ts_str = line.partition("(")[2].partition(")")[0]
                current_ts = dateutil.parser.parse(current_ts_str)
                pass
            elif key == "**** GPU usage ****":
                gpu_power_usage.usage.append(types.SimpleNamespace())
                current_entry = gpu_power_usage.usage[-1]
                current_entry.ts = current_ts

            if not current_entry:
                continue # incomplete ...

            if key == "GPU HW active frequency":
                current_entry.frequency_mhz = float(value.replace(" MHz", ""))

            elif key == "GPU idle residency":
                current_entry.idle_pct = float(value.replace("%", ""))

            elif key == "GPU Power":
                current_entry.power_mw = float(value.replace(" mW", ""))
                current_entry.complete = True

    if gpu_power_usage.usage and "complete" not in gpu_power_usage.usage[-1].__dict__:
        gpu_power_usage.usage.pop()

    return gpu_power_usage


@helpers_store_parsers.ignore_file_not_found
def _parse_virtgpu_memory_metrics(dirname):
    virtgpu_metrics = types.SimpleNamespace()
    virtgpu_metrics.memory = []

    if not artifact_paths.MAC_AI_VIRTGPU_MEMORY:
        logging.info(f"{artifact_dirnames.MAC_AI_VIRTGPU_MEMORY} not found, can't parse the virgpu memory metrics.")
        return None

    current_dt = None
    with open(register_important_file(dirname, artifact_paths.MAC_AI_VIRTGPU_MEMORY / "artifacts" / "memory.txt")) as f:

        for line in f.readlines():
            if line.startswith("total"):
                if not current_dt: continue

                memory = types.SimpleNamespace()
                _, total, _, used, _, free = line.replace(",", "").split()
                memory.used_mb = float(used) / 1024 / 1024
                memory.free_mb = float(free) / 1024 / 1024
                memory.ts = current_dt

                virtgpu_metrics.memory.append(memory)

                pass
            elif line.startswith("ts="):
                current_ts = int(line.partition("=")[-1])
                current_dt = datetime.datetime.fromtimestamp(current_ts)

    return virtgpu_metrics


@helpers_store_parsers.ignore_file_not_found
def _parse_cpu_ram_metrics(dirname):
    cpu_ram_usage = types.SimpleNamespace()
    cpu_ram_usage.memory = []
    cpu_ram_usage.cpu = []

    if not artifact_paths.MAC_AI_CPU_RAM_USAGE:
        return None

    with open(register_important_file(dirname, artifact_paths.MAC_AI_CPU_RAM_USAGE / "artifacts" / "cpu_ram_usage.txt")) as f:

        for line in f.readlines():
            if line.startswith("CPU usage"):
                if not line.strip().endswith("idle"):
                    continue # incomplete line, skip it
                cpu = types.SimpleNamespace()
                idle = line.split()[-2]
                cpu.idle_pct = float(idle[:-1])
                cpu_ram_usage.cpu.append(cpu)

                pass
            elif line.startswith("PhysMem"):
                if not line.strip().endswith("unused."):
                    continue # incomplete line, skip it
                memory = types.SimpleNamespace()
                mem_line = line.split()
                unused = mem_line[-2]
                memory.unused_mb = int(unused[:-1])
                if unused.endswith("G"):
                    memory.unused_mb *= 1024
                cpu_ram_usage.memory.append(memory)
                pass

    return cpu_ram_usage


@helpers_store_parsers.ignore_file_not_found
def _parse_llm_load_test_output(dirname):
    if not artifact_paths.LLM_LOAD_TEST_RUN_DIR:
        return None

    llm_output_file = dirname / artifact_paths.LLM_LOAD_TEST_RUN_DIR / "output" / "output.json"
    register_important_file(dirname, llm_output_file.relative_to(dirname))

    with open(llm_output_file) as f:
        llm_load_test_output = json.load(f)

    return llm_load_test_output


@helpers_store_parsers.ignore_file_not_found
def _parse_llm_load_test_config(dirname):
    if not artifact_paths.LLM_LOAD_TEST_RUN_DIR:
        return None

    llm_config_file = dirname / artifact_paths.LLM_LOAD_TEST_RUN_DIR / "src" / "llm_load_test.config.yaml"
    register_important_file(dirname, llm_config_file.relative_to(dirname))

    llm_load_test_config = types.SimpleNamespace()

    with open(llm_config_file) as f:
        yaml_file = llm_load_test_config.yaml_file = yaml.safe_load(f)

    if not yaml_file:
        logging.error(f"Config file '{llm_config_file}' is empty ...")
        yaml_file = llm_load_test_config.yaml_file = {}

    llm_load_test_config.name = f"llm-load-test config {llm_config_file}"
    llm_load_test_config.get = helpers_store.get_yaml_get_key(llm_load_test_config.name, yaml_file)

    return llm_load_test_config


def _parse_test_start_end(dirname, llm_load_test_output):
    if not llm_load_test_output:
        return None

    test_start_end = types.SimpleNamespace()
    test_start_end.start = None
    test_start_end.end = None

    for result in llm_load_test_output.get("results") or []:
        start = datetime.datetime.fromtimestamp(result["start_time"])
        end = datetime.datetime.fromtimestamp(result["end_time"])

        if test_start_end.start is None or start < test_start_end.start:
            test_start_end.start = start

        if test_start_end.end is None or end > test_start_end.end:
            test_start_end.end = end

    if test_start_end.start is None:
        logging.warning("Could not find the start time of the test...")
    if test_start_end.end is None:
        logging.warning("Could not find the end time of the test...")

    return test_start_end


@helpers_store_parsers.ignore_file_not_found
def _parse_llama_bench_results(dirname):
    bench_dir = (artifact_paths.MAC_AI_REMOTE_LLAMA_CPP_RUN_BENCH or artifact_paths.MAC_AI_REMOTE_RAMALAMA_RUN_BENCH or artifact_paths.LIGHTSPEED_RUN_BENCH)
    if not bench_dir:
        return None

    llama_bench_results = []

    llama_bench_output_file = bench_dir / "artifacts" / "llama-bench.log"

    register_important_file(dirname, llama_bench_output_file)

    with open(dirname / llama_bench_output_file) as f:
        llama_bench_output = f.readlines()

    keys = []
    for line in llama_bench_output:
        if not line.startswith("|"): continue
        line = " ".join(line.strip().split()) # remove the extra spaces

        # remove the extra spaces
        array_values = line.removeprefix("| ").removesuffix(" |").replace(": |", "|").replace(" | ", "|").split("|")

        # skip the split lines
        if "".join(array_values).count("-") > 20: continue
        if not keys:
            keys = array_values
            continue

        results = dict(zip(keys, array_values))
        results["backend"] = results["backend"].split(",")
        results["t/s"], results["t/s err"] = map(float, results["t/s"].split(" ± "))
        results["file_path"] = str(llama_bench_output_file)

        llama_bench_results.append(results)

    return llama_bench_results


@helpers_store_parsers.ignore_file_not_found
def _parse_llama_micro_bench_results(dirname):
    if not artifact_paths.MAC_AI_REMOTE_LLAMA_CPP_RUN_BENCH:
        return None

    llama_micro_bench_results = types.SimpleNamespace()
    llama_micro_bench_results.compute = []
    llama_micro_bench_results.transfer = []

    llama_micro_bench_output_file =  artifact_paths.MAC_AI_REMOTE_LLAMA_CPP_RUN_BENCH / "artifacts" / "test-backend-ops_perf.log"

    with open(register_important_file(dirname, llama_micro_bench_output_file)) as f:
        llama_micro_bench_output = f.readlines()

    llama_micro_bench_results.file_path = str(llama_micro_bench_output_file)

    current_backend = None
    for line in llama_micro_bench_output:
        line = line.strip()

        if line.startswith("Backend "):
            if current_backend in ("Metal", "Vulkan0"):
                break
            current_backend = line.split(": ")[1]

        if not "runs" in line: continue
        # ['ADD(type=f32,ne=[4096,1,1,1],nr=[1,1,1,1]):', '548730', 'runs', '-', '1.84', 'us/run', '-', '48', 'kB/run', '-', '24.84', 'GB/s']
        raw_data = line.replace("\x1b[0m", "").replace("\x1b[1;34m", "").split()

        line_data = types.SimpleNamespace()
        line_data.name = raw_data[0].strip(":")
        line_data.runs = int(raw_data[1])
        line_data.run_duration = float(raw_data[4])
        line_data.run_duration_unit = raw_data[5]
        if line_data.run_duration_unit != "us/run":
            raise ValueError(f"Unexpected duration unit: {line_data.duration_unit}")

        is_compute = "FLOP/run" in raw_data[8]

        if is_compute:
            line_data.run_throughput = float(raw_data[7])
            line_data.run_throughput_unit = raw_data[8]

            if line_data.run_throughput_unit  == "GFLOP/run":
                line_data.run_throughput *= 1000
                line_data.run_throughput_unit = "MFLOP/run"

            if line_data.run_throughput_unit != "MFLOP/run":
                raise ValueError(f"Unexpected duration unit: {line_data.duration_unit}")

            line_data.throughput = float(raw_data[10])
            line_data.throughput_unit = raw_data[11]
            if line_data.throughput_unit  == "TFLOPS":
                line_data.throughput *= 1000
                line_data.throughput_unit = "GFLOPS"

            if line_data.throughput_unit not in ("GFLOPS"):
                import pdb;pdb.set_trace()
                raise ValueError(f"Unexpected throughput unit: {line_data.throughput_unit}")

            dest = llama_micro_bench_results.compute
        else:
            line_data.run_data = float(raw_data[7])
            line_data.run_data_unit = raw_data[8]

            if line_data.run_data_unit != "kB/run":
                raise ValueError(f"Unexpected run data unit: {line_data.run_data_unit}")

            line_data.speed = float(raw_data[10])
            line_data.speed_unit = raw_data[11]

            if line_data.speed_unit not in ("GB/s"):
                import pdb;pdb.set_trace()
                raise ValueError(f"Unexpected speed unit: {line_data.speed_unit}")

            dest = llama_micro_bench_results.transfer
        dest.append(line_data)

    return llama_micro_bench_results


def _parse_system_state(dirname):
    system_state = types.SimpleNamespace()
    if not  artifact_paths.MAC_AI_REMOTE_CAPTURE_SYSTEM_STATE:
        return None

    with open(register_important_file(dirname, artifact_paths.MAC_AI_REMOTE_CAPTURE_SYSTEM_STATE / "artifacts" / "system_profiler.txt")) as f:
        system_state = yaml.safe_load(f)

    return system_state

@helpers_store_parsers.ignore_file_not_found
def _parse_ramalama_commit_info(dirname):
    info_text = (dirname / "ramalama-commit.info").read_text().split("\n")

    ramalama_commit_info = types.SimpleNamespace()
    ramalama_commit_info.date_id = info_text[0]
    ramalama_commit_info.commit_title = info_text[1]
    ramalama_commit_info.commit_hash = info_text[2]

    return ramalama_commit_info

@helpers_store_parsers.ignore_file_not_found
def _parse_lightspeed_info(dirname):
    lightspeed_info = types.SimpleNamespace()

    if artifact_paths.LIGHTSPEED_START_SERVER:
        with open(register_important_file(dirname, artifact_paths.LIGHTSPEED_START_SERVER / "inspect-image.json")) as f:
            inspect_image = json.load(f)

        lightspeed_info.image_date = datetime.datetime.fromisoformat(inspect_image[0]["Created"].rpartition(".")[0])
        lightspeed_info.image_sha = inspect_image[0]["Digest"]

    return lightspeed_info
