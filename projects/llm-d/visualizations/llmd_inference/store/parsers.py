import pathlib
import logging
import datetime
import re
import json
import csv
import types

import projects.matrix_benchmarking.visualizations.helpers.store.parsers as helpers_store_parsers

from ..models import MultiturnBenchmark, GuidellmBenchmark

# Define artifact directory patterns
artifact_dirnames = types.SimpleNamespace()
artifact_dirnames.MULTITURN_BENCHMARK_DIR = "*__llmd__run_multiturn_benchmark"
artifact_dirnames.GUIDELLM_BENCHMARK_DIR = "*__llmd__run_guidellm_benchmark"
artifact_dirnames.PROMETHEUS_UWM_DUMP_DIR = "*__cluster__dump_prometheus_dbs/*__cluster__dump_prometheus_db_uwm"

artifact_paths = types.SimpleNamespace() # will be dynamically populated

# Define important files we want to parse
IMPORTANT_FILES = [
    "exit_code",
    "settings.yaml",

    f"{artifact_dirnames.MULTITURN_BENCHMARK_DIR}/artifacts/multiturn_benchmark_job.logs",
    f"{artifact_dirnames.GUIDELLM_BENCHMARK_DIR}/artifacts/guidellm_benchmark_job.logs",
    f"{artifact_dirnames.PROMETHEUS_UWM_DUMP_DIR}/prometheus.tar.gz",
]


def parse_always(results, dirname, import_settings):
    """Parsed even when reloading from the cache file"""
    results.from_local_env = helpers_store_parsers.parse_local_env(dirname)


def parse_once(results, dirname):
    """Parse the benchmark log files once"""

    # Parse multiturn benchmark
    multiturn_log_path = artifact_paths.MULTITURN_BENCHMARK_DIR / "artifacts/multiturn_benchmark_job.logs"
    if multiturn_log_path and pathlib.Path(multiturn_log_path).exists():
        results.multiturn_benchmark = parse_multiturn_benchmark_log(pathlib.Path(multiturn_log_path))
        logging.info(f"Parsed multiturn benchmark from {multiturn_log_path}")
    else:
        logging.warning(f"Multiturn benchmark log not found at {multiturn_log_path}")
        results.multiturn_benchmark = None

    # Parse guidellm benchmark
    guidellm_log_path = artifact_paths.GUIDELLM_BENCHMARK_DIR / "artifacts/guidellm_benchmark_job.logs"
    if guidellm_log_path and pathlib.Path(guidellm_log_path).exists():
        results.guidellm_benchmarks = parse_guidellm_benchmark_log(pathlib.Path(guidellm_log_path))
        logging.info(f"Parsed {len(results.guidellm_benchmarks)} guidellm benchmarks from {guidellm_log_path}")
    else:
        logging.warning(f"Guidellm benchmark log not found at {guidellm_log_path}")
        results.guidellm_benchmarks = []

    # Parse test metadata
    exit_code_path = "exit_code"
    if exit_code_path and pathlib.Path(exit_code_path).exists():
        with open(exit_code_path, 'r') as f:
            exit_code = f.read().strip()
            results.test_success = (exit_code == "0")
            logging.info(f"Test exit code: {exit_code}, success: {results.test_success}")
    else:
        results.test_success = None
        logging.warning(f"Exit code file not found at {exit_code_path}")

def parse_multiturn_benchmark_log(log_file_path: pathlib.Path) -> MultiturnBenchmark:
    """Parse multiturn benchmark log file and extract metrics"""

    if not log_file_path.exists():
        logging.warning(f"Multiturn benchmark log not found: {log_file_path}")
        return None

    with open(log_file_path, 'r') as f:
        content = f.read()

    benchmark = MultiturnBenchmark(
        total_time=0, total_requests=0, completed_conversations=0,
        total_conversations=0, requests_per_second=0,
        ttft_min=0, ttft_max=0, ttft_mean=0, ttft_p50=0, ttft_p95=0, ttft_p99=0,
        total_request_time_min=0, total_request_time_max=0, total_request_time_mean=0,
        total_request_time_p50=0, total_request_time_p95=0
    )

    # Parse summary section
    summary_match = re.search(r'BENCHMARK SUMMARY\s*=+\s*(.*?)(?:TTFT by Turn Number|=+|\Z)', content, re.DOTALL)
    if summary_match:
        summary_text = summary_match.group(1)

        # Parse basic metrics
        if match := re.search(r'Total time:\s*(\d+\.?\d*)s', summary_text):
            benchmark.total_time = float(match.group(1))

        if match := re.search(r'Total requests:\s*(\d+)', summary_text):
            benchmark.total_requests = int(match.group(1))

        if match := re.search(r'Completed conversations:\s*(\d+)/(\d+)', summary_text):
            benchmark.completed_conversations = int(match.group(1))
            benchmark.total_conversations = int(match.group(2))

        if match := re.search(r'Requests per second:\s*(\d+\.?\d*)', summary_text):
            benchmark.requests_per_second = float(match.group(1))

        # Parse TTFT metrics
        ttft_section = re.search(r'Time to First Token \(TTFT\):\s*(.*?)(?:Total Request Time:|$)', summary_text, re.DOTALL)
        if ttft_section:
            ttft_text = ttft_section.group(1)

            if match := re.search(r'Min:\s*(\d+\.?\d*)\s*ms', ttft_text):
                benchmark.ttft_min = float(match.group(1))
            if match := re.search(r'Max:\s*(\d+\.?\d*)\s*ms', ttft_text):
                benchmark.ttft_max = float(match.group(1))
            if match := re.search(r'Mean:\s*(\d+\.?\d*)\s*ms', ttft_text):
                benchmark.ttft_mean = float(match.group(1))
            if match := re.search(r'P50:\s*(\d+\.?\d*)\s*ms', ttft_text):
                benchmark.ttft_p50 = float(match.group(1))
            if match := re.search(r'P95:\s*(\d+\.?\d*)\s*ms', ttft_text):
                benchmark.ttft_p95 = float(match.group(1))
            if match := re.search(r'P99:\s*(\d+\.?\d*)\s*ms', ttft_text):
                benchmark.ttft_p99 = float(match.group(1))

        # Parse Total Request Time metrics
        total_time_section = re.search(r'Total Request Time:\s*(.*?)(?:TTFT by Turn Number:|$)', summary_text, re.DOTALL)
        if total_time_section:
            total_time_text = total_time_section.group(1)

            if match := re.search(r'Min:\s*(\d+\.?\d*)\s*ms', total_time_text):
                benchmark.total_request_time_min = float(match.group(1))
            if match := re.search(r'Max:\s*(\d+\.?\d*)\s*ms', total_time_text):
                benchmark.total_request_time_max = float(match.group(1))
            if match := re.search(r'Mean:\s*(\d+\.?\d*)\s*ms', total_time_text):
                benchmark.total_request_time_mean = float(match.group(1))
            if match := re.search(r'P50:\s*(\d+\.?\d*)\s*ms', total_time_text):
                benchmark.total_request_time_p50 = float(match.group(1))
            if match := re.search(r'P95:\s*(\d+\.?\d*)\s*ms', total_time_text):
                benchmark.total_request_time_p95 = float(match.group(1))

    # Parse TTFT by turn number
    turn_section = re.search(r'TTFT by Turn Number:\s*(.*?)(?:TTFT by Document Type:|$)', content, re.DOTALL)
    if turn_section:
        turn_text = turn_section.group(1)
        for line in turn_text.strip().split('\n'):
            if match := re.search(r'Turn\s+(\d+):\s*(\d+\.?\d*)\s*ms\s*avg', line):
                turn_num = int(match.group(1))
                avg_ttft = float(match.group(2))
                benchmark.ttft_by_turn[turn_num] = avg_ttft

    # Parse TTFT by document type
    doc_type_section = re.search(r'TTFT by Document Type:\s*(.*?)(?:First Turn vs Subsequent Turns|$)', content, re.DOTALL)
    if doc_type_section:
        doc_type_text = doc_type_section.group(1)
        for line in doc_type_text.strip().split('\n'):
            if match := re.search(r'(\w+):\s*(\d+\.?\d*)\s*ms\s*avg', line):
                doc_type = match.group(1)
                avg_ttft = float(match.group(2))
                benchmark.ttft_by_doc_type[doc_type] = avg_ttft

    # Parse first turn vs subsequent turns
    speedup_section = re.search(r'First Turn vs Subsequent Turns.*?:\s*(.*?)(?:=+|\Z)', content, re.DOTALL)
    if speedup_section:
        speedup_text = speedup_section.group(1)

        if match := re.search(r'First turn avg:\s*(\d+\.?\d*)\s*ms', speedup_text):
            benchmark.first_turn_avg = float(match.group(1))
        if match := re.search(r'Later turns avg:\s*(\d+\.?\d*)\s*ms', speedup_text):
            benchmark.later_turns_avg = float(match.group(1))
        if match := re.search(r'Speedup ratio:\s*(\d+\.?\d*)x', speedup_text):
            benchmark.speedup_ratio = float(match.group(1))

    return benchmark

def parse_guidellm_benchmark_log(log_file_path: pathlib.Path) -> list[GuidellmBenchmark]:
    """Parse Guidellm benchmark log file and extract metrics for each strategy"""

    if not log_file_path.exists():
        logging.warning(f"Guidellm benchmark log not found: {log_file_path}")
        return []

    with open(log_file_path, 'r') as f:
        content = f.read()

    benchmarks = []

    # Parse the latency statistics table
    latency_match = re.search(r'Request Latency Statistics.*?\n(.*?)(?:\n\n|\Z)', content, re.DOTALL)
    if not latency_match:
        logging.warning("Could not find latency statistics table in Guidellm log")
        return benchmarks

    latency_table = latency_match.group(1)

    # Parse the throughput statistics table
    throughput_match = re.search(r'Server Throughput Statistics.*?\n(.*?)(?:\n\n|\Z)', content, re.DOTALL)
    if not throughput_match:
        logging.warning("Could not find throughput statistics table in Guidellm log")
        return benchmarks

    throughput_table = throughput_match.group(1)

    # Parse each row of the latency table
    latency_lines = [line.strip() for line in latency_table.split('\n') if '|' in line and not line.startswith('|===')]
    throughput_lines = [line.strip() for line in throughput_table.split('\n') if '|' in line and not line.startswith('|===')]

    for i, latency_line in enumerate(latency_lines):
        if i >= len(throughput_lines):
            break

        # Parse latency row
        latency_parts = [part.strip() for part in latency_line.split('|') if part.strip()]
        if len(latency_parts) < 9:
            continue

        strategy = latency_parts[0]
        if strategy in ['Benchmark', 'Strategy'] or '------' in strategy:
            continue

        # Parse throughput row
        throughput_parts = [part.strip() for part in throughput_lines[i].split('|') if part.strip()]
        if len(throughput_parts) < 11:
            continue

        try:
            benchmark = GuidellmBenchmark(
                strategy=strategy,
                duration=30.0,  # From the sweep profile config
                warmup_time=0.0,
                cooldown_time=0.0,

                # From throughput table
                request_rate=float(throughput_parts[2]) if throughput_parts[2] != '' else 0.0,
                request_concurrency=float(throughput_parts[4]) if throughput_parts[4] != '' else 0.0,
                completed_requests=0,  # Not directly available in this format
                failed_requests=0,

                # Token metrics per request (calculated from per-second rates and request rate)
                input_tokens_per_request=float(throughput_parts[6]) / float(throughput_parts[2]) if throughput_parts[2] and float(throughput_parts[2]) > 0 else 0.0,
                output_tokens_per_request=float(throughput_parts[8]) / float(throughput_parts[2]) if throughput_parts[2] and float(throughput_parts[2]) > 0 else 0.0,
                total_tokens_per_request=float(throughput_parts[10]) / float(throughput_parts[2]) if throughput_parts[2] and float(throughput_parts[2]) > 0 else 0.0,

                # From latency table
                request_latency_median=float(latency_parts[1]) if latency_parts[1] != '' else 0.0,
                request_latency_p95=float(latency_parts[2]) if latency_parts[2] != '' else 0.0,
                ttft_median=float(latency_parts[3]) if latency_parts[3] != '' else 0.0,
                ttft_p95=float(latency_parts[4]) if latency_parts[4] != '' else 0.0,
                itl_median=float(latency_parts[5]) if latency_parts[5] != '' else 0.0,
                itl_p95=float(latency_parts[6]) if latency_parts[6] != '' else 0.0,
                tpot_median=float(latency_parts[7]) if latency_parts[7] != '' else 0.0,
                tpot_p95=float(latency_parts[8]) if latency_parts[8] != '' else 0.0,

                # From throughput table
                tokens_per_second=float(throughput_parts[10]) if throughput_parts[10] != '' else 0.0,
                input_tokens_per_second=float(throughput_parts[6]) if throughput_parts[6] != '' else 0.0,
                output_tokens_per_second=float(throughput_parts[8]) if throughput_parts[8] != '' else 0.0,
            )

            benchmarks.append(benchmark)

        except (ValueError, IndexError) as e:
            logging.warning(f"Failed to parse Guidellm benchmark row: {e}")
            continue

    return benchmarks
