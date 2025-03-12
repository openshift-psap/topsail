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

artifact_paths = types.SimpleNamespace() # will be dynamically populated

IMPORTANT_FILES = [
    "config.yaml",
    ".uuid",

    f"{artifact_dirnames.LLM_LOAD_TEST_RUN_DIR}/output/output.json",
    f"{artifact_dirnames.LLM_LOAD_TEST_RUN_DIR}/src/llm_load_test.config.yaml",

    f"{artifact_dirnames.MAC_AI_POWER_USAGE_GPU}/artifacts/power_usage.txt",
    f"{artifact_dirnames.MAC_AI_CPU_RAM_USAGE}/artifacts/cpu_ram_usage.txt",
    f"{artifact_dirnames.MAC_AI_VIRTGPU_MEMORY}/artifacts/memory.txt",

    f"{artifact_dirnames.MAC_AI_REMOTE_LLAMA_CPP_RUN_MODEL}/artifacts/build.*.log",

    f"{artifact_dirnames.MAC_AI_REMOTE_LLAMA_CPP_RUN_BENCH}/artifacts/llama-bench.log",
]


def parse_always(results, dirname, import_settings):
    # parsed even when reloading from the cache file

    results.from_local_env = helpers_store_parsers.parse_local_env(dirname)


def parse_once(results, dirname):
    results.test_config = helpers_store_parsers.parse_test_config(dirname)

    results.test_uuid = helpers_store_parsers.parse_test_uuid(dirname)

    results.llm_load_test_config = _parse_llm_load_test_config(dirname)
    results.llm_load_test_output = _parse_llm_load_test_output(dirname)
    results.gpu_power_usage = _parse_gpu_power_metrics(dirname)
    results.cpu_ram_usage = _parse_cpu_ram_metrics(dirname)
    results.virtgpu_metrics = _parse_virtgpu_memory_metrics(dirname)
    results.file_links = _parse_file_links(dirname)

    results.llama_bench_results = _parse_llama_bench_results(dirname)

    results.test_start_end = _parse_test_start_end(dirname, results.llm_load_test_output)


def _parse_file_links(dirname):
    file_links = types.SimpleNamespace()

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
                cpu = types.SimpleNamespace()
                idle = line.split()[-2]
                cpu.idle_pct = float(idle[:-1])
                cpu_ram_usage.cpu.append(cpu)

                pass
            elif line.startswith("PhysMem"):
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
    llm_output_file = dirname / artifact_paths.LLM_LOAD_TEST_RUN_DIR / "output" / "output.json"
    register_important_file(dirname, llm_output_file.relative_to(dirname))

    with open(llm_output_file) as f:
        llm_load_test_output = json.load(f)

    return llm_load_test_output


@helpers_store_parsers.ignore_file_not_found
def _parse_llm_load_test_config(dirname):
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
    if not artifact_paths.MAC_AI_REMOTE_LLAMA_CPP_RUN_BENCH:
        return None
    llama_bench_results = []

    llama_bench_output_file =  artifact_paths.MAC_AI_REMOTE_LLAMA_CPP_RUN_BENCH / "artifacts" / "llama-bench.log"
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
