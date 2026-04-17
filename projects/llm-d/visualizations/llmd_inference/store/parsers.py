import pathlib
import logging
import datetime
import re
import json
import csv
import types
import glob

import projects.matrix_benchmarking.visualizations.helpers.store.prom as helper_prom_store
import projects.matrix_benchmarking.visualizations.helpers.store.parsers as helpers_store_parsers

from ..models import GuidellmBenchmark

register_important_file = None # will be when importing store/__init__.py

# Define artifact directory patterns
artifact_dirnames = types.SimpleNamespace()
artifact_dirnames.GUIDELLM_BENCHMARK_DIR = "*__llmd__run_guidellm_benchmark"
artifact_dirnames.PROMETHEUS_DUMP_DIR = "*__cluster__dump_prometheus_dbs/*__cluster__dump_prometheus_db"
artifact_dirnames.PROMETHEUS_UWM_DUMP_DIR = "*__cluster__dump_prometheus_dbs/*__cluster__dump_prometheus_db_uwm"
artifact_dirnames.LLMISVC_CAPTURE_DIR = "*__llmd__capture_isvc_state"

artifact_paths = types.SimpleNamespace() # will be dynamically populated

# Define important files we want to parse
IMPORTANT_FILES = [
    "exit_code",
    "settings.yaml",

    # Note: GuideLLM benchmark files are now handled dynamically in parse_once()
    # to support multiple benchmark directories (multi-rate scenarios)
    f"{artifact_dirnames.PROMETHEUS_DUMP_DIR}/prometheus.t*",
    f"{artifact_dirnames.PROMETHEUS_UWM_DUMP_DIR}/prometheus.t*",
    f"{artifact_dirnames.GUIDELLM_BENCHMARK_DIR}/artifacts/results/benchmarks.json",
    f"{artifact_dirnames.GUIDELLM_BENCHMARK_DIR}/artifacts/guidellm_benchmark_job.logs",
    f"{artifact_dirnames.LLMISVC_CAPTURE_DIR}/artifacts/llminferenceservice.json",
]


def parse_always(results, dirname, import_settings):
    """Parsed even when reloading from the cache file"""
    results.from_local_env = helpers_store_parsers.parse_local_env(dirname)


def find_guidellm_benchmark_directories(dirname):
    """Find all guidellm benchmark directories, including multi-rate directories"""
    # Look for all directories matching the guidellm benchmark pattern
    # This includes both single directory and multi-rate directories
    pattern = "*__llmd__run_guidellm_benchmark*"
    guidellm_dirs = []

    for path in glob.glob(str(dirname / pattern)):
        path_obj = pathlib.Path(path)
        if path_obj.is_dir():
            guidellm_dirs.append(path_obj)

    # Sort to ensure consistent ordering
    return sorted(guidellm_dirs)

def parse_once(results, dirname):
    """Parse the benchmark log files once"""

    # Parse test configuration and environment for PROW URLs
    results.from_env = helpers_store_parsers.parse_env(dirname, None, artifact_paths.LLMISVC_CAPTURE_DIR)

    # Parse guidellm benchmarks - support multiple benchmark directories
    results.guidellm_benchmarks = []
    results.guidellm_configuration = None
    guidellm_directories = find_guidellm_benchmark_directories(dirname)

    if guidellm_directories:
        for guidellm_dir in guidellm_directories:
            # Check for JSON file first, fallback to log file
            json_file_path = guidellm_dir / "artifacts" / "results" / "benchmarks.json"
            log_file_path = guidellm_dir / "artifacts" / "guidellm_benchmark_job.logs"

            if json_file_path.exists():
                benchmarks = parse_guidellm_benchmark_json(dirname, json_file_path.relative_to(dirname))
                results.guidellm_benchmarks.extend(benchmarks)
                logging.info(f"Parsed {len(benchmarks)} guidellm benchmarks from JSON: {json_file_path}")

                # Parse configuration from the first JSON file found
                if results.guidellm_configuration is None:
                    results.guidellm_configuration = _parse_guidellm_config(dirname, json_file_path.relative_to(dirname))

            elif log_file_path.exists():
                raise RuntimeError("Don't want to use log-file parsing (hardcoded)")
                benchmarks = parse_guidellm_benchmark_log(dirname, log_file_path.relative_to(dirname))
                results.guidellm_benchmarks.extend(benchmarks)
                logging.info(f"Parsed {len(benchmarks)} guidellm benchmarks from log: {log_file_path}")
            else:
                logging.warning(f"Neither JSON nor log file found in {guidellm_dir / 'artifacts'}")

        logging.info(f"Total parsed guidellm benchmarks: {len(results.guidellm_benchmarks)}")
    else:
        logging.warning("No guidellm benchmark directories found")

    # Parse test metadata
    exit_code_path = "exit_code"
    if exit_code_path and (dirname / exit_code_path).exists():
        with open(register_important_file(dirname, exit_code_path)) as f:
            exit_code = f.read().strip()
            results.test_success = (exit_code == "0")
            logging.info(f"Test exit code: {exit_code}, success: {results.test_success}")
    else:
        results.test_success = None
        logging.warning(f"Exit code file not found at {exit_code_path}")

    # Parse LLMISVC configuration
    results.llmisvc_config = _parse_llmisvc_config(dirname)

    # Parse Prometheus UWM metrics
    results.metrics = _extract_metrics(dirname)

def parse_guidellm_benchmark_log(dirname, log_file_path: pathlib.Path) -> list[GuidellmBenchmark]:
    """Parse Guidellm benchmark log file and extract metrics for each strategy"""

    if not (dirname / log_file_path).exists():
        logging.warning(f"Guidellm benchmark log not found: {log_file_path}")
        return []

    with open(register_important_file(dirname, log_file_path)) as f:
        content = f.read()

    logging.debug(f"Parsing GuideLLM log file: {log_file_path} (length: {len(content)} chars)")

    # Check if log contains the expected output format
    if "Run Summary Info" not in content:
        logging.warning(f"GuideLLM log appears to be incomplete or malformed - no 'Run Summary Info' section found in {log_file_path}")
        return []

    benchmarks = []

    # Parse the Run Summary Info table for basic info
    summary_match = re.search(r'ℹ Run Summary Info.*?\n(.*?)(?=ℹ Text Metrics Statistics|\Z)', content, re.DOTALL)
    if not summary_match:
        logging.warning("Could not find Run Summary Info table in Guidellm log")
        return benchmarks

    summary_table = summary_match.group(1)

    # Parse the Request Latency Statistics table
    latency_match = re.search(r'ℹ Request Latency Statistics.*?\n(.*?)(?=ℹ Server Throughput Statistics|\Z)', content, re.DOTALL)
    if not latency_match:
        logging.warning("Could not find Request Latency Statistics table in Guidellm log")
        return benchmarks

    latency_table = latency_match.group(1)

    # Parse the Server Throughput Statistics table
    throughput_match = re.search(r'ℹ Server Throughput Statistics.*?\n(.*?)(?=\n\n|\Z)', content, re.DOTALL)
    if not throughput_match:
        logging.warning("Could not find Server Throughput Statistics table in Guidellm log")
        return benchmarks

    throughput_table = throughput_match.group(1)

    # Extract data rows (skip headers and separators)
    def extract_data_rows(table_text):
        lines = [line.strip() for line in table_text.split('\n') if line.strip()]
        data_rows = []
        for line in lines:
            if '|' in line and not line.startswith('|===') and 'Benchmark' not in line and 'Strategy' not in line and '------' not in line:
                data_rows.append(line)
        return data_rows

    summary_rows = extract_data_rows(summary_table)
    latency_rows = extract_data_rows(latency_table)
    throughput_rows = extract_data_rows(throughput_table)

    # Parse each benchmark strategy
    for i, summary_row in enumerate(summary_rows):
        if i >= len(latency_rows) or i >= len(throughput_rows):
            break

        try:
            # Parse summary row: | concurrent | 17:10:09 | 17:11:09 | 60.0 | 0.0  | 0.0  | 6809.0   | 0.0       | 0.0 | 3048.0 | 0.0     | 0.0 |
            summary_parts = [part.strip() for part in summary_row.split('|') if part.strip()]
            if len(summary_parts) < 12:
                continue

            strategy = summary_parts[0]
            duration = float(summary_parts[3]) if summary_parts[3] else 60.0
            warmup_time = float(summary_parts[4]) if summary_parts[4] else 0.0
            cooldown_time = float(summary_parts[5]) if summary_parts[5] else 0.0
            input_tokens_comp = float(summary_parts[6]) if summary_parts[6] else 0.0
            output_tokens_comp = float(summary_parts[9]) if summary_parts[9] else 0.0

            # Parse latency row: | concurrent | 68.6    | 68.6   | 1366.9  | 1366.9  | 22.1  | 22.1   | 22.5  | 22.5   |
            latency_parts = [part.strip() for part in latency_rows[i].split('|') if part.strip()]
            if len(latency_parts) < 9:
                continue

            request_latency_median = float(latency_parts[1]) if latency_parts[1] else 0.0
            request_latency_p95 = float(latency_parts[2]) if latency_parts[2] else 0.0
            ttft_median = float(latency_parts[3]) if latency_parts[3] else 0.0
            ttft_p95 = float(latency_parts[4]) if latency_parts[4] else 0.0
            itl_median = float(latency_parts[5]) if latency_parts[5] else 0.0
            itl_p95 = float(latency_parts[6]) if latency_parts[6] else 0.0
            tpot_median = float(latency_parts[7]) if latency_parts[7] else 0.0
            tpot_p95 = float(latency_parts[8]) if latency_parts[8] else 0.0

            # Parse throughput row: | concurrent | 1.0   | 1.0   | 0.0     | 0.0          | 45.3          | 146.5        |
            throughput_parts = [part.strip() for part in throughput_rows[i].split('|') if part.strip()]
            if len(throughput_parts) < 7:
                continue

            concurrency_median = float(throughput_parts[1]) if throughput_parts[1] else 0.0
            concurrency_mean = float(throughput_parts[2]) if throughput_parts[2] else 0.0
            request_rate = float(throughput_parts[3]) if throughput_parts[3] else 0.0
            input_tokens_per_second = float(throughput_parts[4]) if throughput_parts[4] else 0.0
            output_tokens_per_second = float(throughput_parts[5]) if throughput_parts[5] else 0.0
            total_tokens_per_second = float(throughput_parts[6]) if throughput_parts[6] else 0.0

            # Calculate requests completed during the run
            completed_requests = int(request_rate * duration) if request_rate > 0 else 0

            # Calculate tokens per request
            input_tokens_per_request = (input_tokens_per_second / request_rate) if request_rate > 0 else 0.0
            output_tokens_per_request = (output_tokens_per_second / request_rate) if request_rate > 0 else 0.0
            total_tokens_per_request = (total_tokens_per_second / request_rate) if request_rate > 0 else 0.0

            benchmark = GuidellmBenchmark(
                strategy=strategy,
                duration=duration,
                warmup_time=warmup_time,
                cooldown_time=cooldown_time,

                # Request metrics
                request_rate=request_rate,
                request_concurrency=concurrency_mean,
                completed_requests=completed_requests,
                failed_requests=0,  # Not available in current format

                # Token metrics per request
                input_tokens_per_request=input_tokens_per_request,
                output_tokens_per_request=output_tokens_per_request,
                total_tokens_per_request=total_tokens_per_request,

                # Latency metrics (convert to consistent units)
                request_latency_median=request_latency_median / 1000.0,  # Convert ms to seconds
                request_latency_p95=request_latency_p95 / 1000.0,        # Convert ms to seconds
                ttft_median=ttft_median / 1000.0,    # Convert ms to seconds
                ttft_p95=ttft_p95 / 1000.0,          # Convert ms to seconds
                itl_median=itl_median / 1000.0,      # Convert ms to seconds
                itl_p95=itl_p95 / 1000.0,            # Convert ms to seconds
                tpot_median=tpot_median / 1000.0,    # Convert ms to seconds
                tpot_p95=tpot_p95 / 1000.0,          # Convert ms to seconds

                # Throughput metrics
                tokens_per_second=total_tokens_per_second,
                input_tokens_per_second=input_tokens_per_second,
                output_tokens_per_second=output_tokens_per_second,
            )

            benchmarks.append(benchmark)
            logging.info(f"Parsed Guidellm benchmark: {strategy}, rate={request_rate:.2f} req/s, concurrency={concurrency_mean:.1f}, tokens/s={total_tokens_per_second:.1f}")

            # Highlight unexpected throughput values
            if total_tokens_per_second > 1000 or total_tokens_per_second < 1:
                logging.warning(f"Unusual tokens/second value: {total_tokens_per_second:.1f} for strategy {strategy}")

            # Debug logging for troubleshooting
            logging.debug(f"  Raw parsed values for {strategy}:")
            logging.debug(f"    Latency: TTFT={ttft_median:.3f}ms, TPOT={tpot_median:.3f}ms, ITL={itl_median:.3f}ms")
            logging.debug(f"    Request Latency: median={request_latency_median:.3f}ms, p95={request_latency_p95:.3f}ms")
            logging.debug(f"    Throughput: input={input_tokens_per_second:.1f}, output={output_tokens_per_second:.1f}, total={total_tokens_per_second:.1f}")
            logging.debug(f"    Raw table rows:")
            logging.debug(f"      Summary: {summary_row}")
            logging.debug(f"      Latency: {latency_rows[i]}")
            logging.debug(f"      Throughput: {throughput_rows[i]}")

        except (ValueError, IndexError) as e:
            logging.warning(f"Failed to parse Guidellm benchmark row {i}: {e}")
            logging.debug(f"  Problem row data:")
            logging.debug(f"    Summary row: {summary_row}")
            if i < len(latency_rows):
                logging.debug(f"    Latency row: {latency_rows[i]}")
            if i < len(throughput_rows):
                logging.debug(f"    Throughput row: {throughput_rows[i]}")
            continue

    return benchmarks


def parse_guidellm_benchmark_json(dirname, json_file_path: pathlib.Path) -> list[GuidellmBenchmark]:
    """Parse Guidellm benchmark JSON file and extract metrics"""

    if not (dirname / json_file_path).exists():
        logging.warning(f"Guidellm benchmark JSON not found: {json_file_path}")
        return []

    try:
        with open(register_important_file(dirname, json_file_path)) as f:
            json_data = json.load(f)

        logging.debug(f"Parsing GuideLLM JSON file: {json_file_path} (found {len(json_data.get('benchmarks', []))} benchmarks)")

        benchmarks = []

        # Parse each benchmark in the JSON
        for benchmark_data in json_data.get('benchmarks', []):
            try:
                # Extract strategy and concurrency info with fallback logic
                scheduler = benchmark_data.get('scheduler', {})
                config = benchmark_data.get('config', {})
                strategy_info = config.get('strategy', {})
                strategy = strategy_info.get('type_', 'unknown')

                # Try multiple paths for concurrency extraction
                concurrency = 1.0
                concurrency_source = "default"
                try:
                    # First try: scheduler.strategy.streams
                    concurrency = float(strategy_info.get('streams', 0))
                    if concurrency <= 0:
                        raise ValueError("Invalid streams value")
                    concurrency_source = "config.strategy.streams"
                except (ValueError, TypeError):
                    try:
                        # Second try: profile.stream
                        sched_strategy = scheduler.get("strategy", {})
                        streams = sched_strategy.get('streams')
                        if not streams or streams <= 0:
                            raise ValueError("No valid streams found")
                        concurrency = float(streams)
                        concurrency_source = "profile.scheduler.streams"

                    except (ValueError, TypeError, IndexError):
                        logging.warning(f"Could not find concurrency 'streams' for benchmark. Using default value 1.0")
                        concurrency = 1.0
                        concurrency_source = "default"

                # Extract timing info
                state = scheduler.get('state', {})
                start_time = state.get('start_time', 0)
                end_time = state.get('end_time', 0)
                duration = end_time - start_time if end_time > start_time else 60.0

                # Extract metrics
                metrics = benchmark_data.get('metrics', {})

                # Helper function to safely extract metric values
                def get_metric_value(metric_name, stat_type='median', default=0.0, fail_if_missing=False):
                    metric_data = metrics.get(metric_name, {}).get('successful', {})
                    if stat_type in ['p95', 'p90', 'p75', 'p50', 'p25', 'p10']:
                        percentiles = metric_data.get('percentiles', {})
                        if stat_type not in percentiles:
                            if fail_if_missing:
                                raise KeyError(f"Percentile {stat_type} not found in {metric_name} percentiles: {list(percentiles.keys())}")
                            return default
                        return float(percentiles[stat_type])
                    else:
                        if stat_type not in metric_data:
                            if fail_if_missing:
                                raise KeyError(f"Stat type {stat_type} not found in {metric_name} successful data: {list(metric_data.keys())}")
                            return default
                        return float(metric_data[stat_type])

                # Extract latency metrics (convert ms to seconds for consistency)
                request_latency_median = get_metric_value('request_latency', 'median') / 1000.0
                request_latency_p95 = get_metric_value('request_latency', 'p95') / 1000.0
                ttft_median = get_metric_value('time_to_first_token_ms', 'median') / 1000.0
                ttft_p95 = get_metric_value('time_to_first_token_ms', 'p95') / 1000.0
                itl_median = get_metric_value('inter_token_latency_ms', 'median') / 1000.0
                itl_p95 = get_metric_value('inter_token_latency_ms', 'p95') / 1000.0
                tpot_median = get_metric_value('time_per_output_token_ms', 'median') / 1000.0
                tpot_p95 = get_metric_value('time_per_output_token_ms', 'p95') / 1000.0

                # Extract throughput metrics
                request_rate = get_metric_value('requests_per_second', 'mean')
                input_tokens_per_second = get_metric_value('input_tokens_per_second', 'mean')
                output_tokens_per_second = get_metric_value('output_tokens_per_second', 'mean')
                total_tokens_per_second = input_tokens_per_second + output_tokens_per_second

                # Extract output token percentiles (will fail if not available)
                output_tokens_per_second_p10 = get_metric_value('output_tokens_per_second', 'p10', fail_if_missing=True)
                output_tokens_per_second_p25 = get_metric_value('output_tokens_per_second', 'p25', fail_if_missing=True)
                output_tokens_per_second_p50 = get_metric_value('output_tokens_per_second', 'p50', fail_if_missing=True)
                output_tokens_per_second_p75 = get_metric_value('output_tokens_per_second', 'p75', fail_if_missing=True)
                output_tokens_per_second_p90 = get_metric_value('output_tokens_per_second', 'p90', fail_if_missing=True)

                # Calculate requests completed and tokens per request
                completed_requests = int(request_rate * duration) if request_rate > 0 else 0
                input_tokens_per_request = (input_tokens_per_second / request_rate) if request_rate > 0 else 0.0
                output_tokens_per_request = (output_tokens_per_second / request_rate) if request_rate > 0 else 0.0
                total_tokens_per_request = (total_tokens_per_second / request_rate) if request_rate > 0 else 0.0

                # Create GuidellmBenchmark object
                benchmark = GuidellmBenchmark(
                    strategy=strategy,
                    duration=duration,
                    warmup_time=0.0,  # Not available in JSON format
                    cooldown_time=0.0,  # Not available in JSON format

                    # Request metrics
                    request_rate=request_rate,
                    request_concurrency=concurrency,
                    completed_requests=completed_requests,
                    failed_requests=0,  # Could extract from unsuccessful metrics if needed

                    # Token metrics per request
                    input_tokens_per_request=input_tokens_per_request,
                    output_tokens_per_request=output_tokens_per_request,
                    total_tokens_per_request=total_tokens_per_request,

                    # Latency metrics (already in seconds)
                    request_latency_median=request_latency_median,
                    request_latency_p95=request_latency_p95,
                    ttft_median=ttft_median,
                    ttft_p95=ttft_p95,
                    itl_median=itl_median,
                    itl_p95=itl_p95,
                    tpot_median=tpot_median,
                    tpot_p95=tpot_p95,

                    # Throughput metrics
                    tokens_per_second=total_tokens_per_second,
                    input_tokens_per_second=input_tokens_per_second,
                    output_tokens_per_second=output_tokens_per_second,

                    # Output token percentiles
                    output_tokens_per_second_p10=output_tokens_per_second_p10,
                    output_tokens_per_second_p25=output_tokens_per_second_p25,
                    output_tokens_per_second_p50=output_tokens_per_second_p50,
                    output_tokens_per_second_p75=output_tokens_per_second_p75,
                    output_tokens_per_second_p90=output_tokens_per_second_p90,
                )

                benchmarks.append(benchmark)
                logging.info(f"Parsed JSON benchmark: {strategy}, rate={request_rate:.2f} req/s, concurrency={concurrency:.1f} (from {concurrency_source}), tokens/s={total_tokens_per_second:.1f}")

                # Debug logging
                logging.debug(f"  JSON parsed values for {strategy}:")
                logging.debug(f"    Concurrency: {concurrency:.1f} (extracted from {concurrency_source})")
                logging.debug(f"    Latency: TTFT={ttft_median*1000:.3f}ms, TPOT={tpot_median*1000:.3f}ms, ITL={itl_median*1000:.3f}ms")
                logging.debug(f"    Request Latency: median={request_latency_median*1000:.3f}ms, p95={request_latency_p95*1000:.3f}ms")
                logging.debug(f"    Throughput: input={input_tokens_per_second:.1f}, output={output_tokens_per_second:.1f}, total={total_tokens_per_second:.1f}")

            except (KeyError, ValueError, TypeError) as e:
                logging.warning(f"Failed to parse benchmark data in JSON: {e}")
                logging.debug(f"Problematic benchmark data: {benchmark_data}")
                continue

        return benchmarks

    except (json.JSONDecodeError, ValueError) as e:
        logging.warning(f"Failed to parse Guidellm JSON {json_file_path}: {e}")
        return []


def _parse_guidellm_config(dirname, json_file_path: pathlib.Path):
    """Parse GuideLLM configuration from JSON file"""

    if not (dirname / json_file_path).exists():
        logging.warning(f"GuideLLM JSON config file not found: {json_file_path}")
        return None

    try:
        with open(register_important_file(dirname, json_file_path)) as f:
            json_data = json.load(f)

        # Extract top-level configuration fields
        config = {}

        # Extract args if present
        if 'args' in json_data and json_data['args']:
            config['args'] = json_data['args']
        if 'metadata' in json_data and json_data['metadata']:
            config['metadata'] = json_data['metadata']

        logging.info(f"Successfully parsed GuideLLM configuration from {json_file_path}")

        return config if config else None

    except Exception as e:
        logging.error(f"Failed to parse GuideLLM configuration from {json_file_path}: {e}")
        return None


def _parse_llmisvc_config(dirname):
    """Parse LLMISVC configuration from captured state artifacts"""
    if artifact_paths.LLMISVC_CAPTURE_DIR is None:
        logging.warning("LLMISVC capture directory not found")
        return None

    llmisvc_config_path = artifact_paths.LLMISVC_CAPTURE_DIR / "artifacts" / "llminferenceservice.json"

    if not (dirname / llmisvc_config_path).exists():
        logging.warning(f"LLMISVC config file not found at {llmisvc_config_path}")
        return None

    try:
        with open(register_important_file(dirname, llmisvc_config_path)) as f:
            llmisvc_config = json.load(f)
            logging.info(f"Successfully parsed LLMISVC configuration from {llmisvc_config_path}")
            return llmisvc_config
    except Exception as e:
        logging.error(f"Failed to parse LLMISVC configuration from {llmisvc_config_path}: {e}")
        return None


def _extract_metrics(dirname):
    """Extract Prometheus metrics from main and UWM database files"""
    db_files = {}

    # Add main Prometheus metrics (cluster-level: node, kube, nvidia, etc.)
    if artifact_paths.PROMETHEUS_DUMP_DIR is not None:
        db_files["sutest"] = (str(artifact_paths.PROMETHEUS_DUMP_DIR / "prometheus.t*"), get_llmd_main_metrics())

    # Add UWM Prometheus metrics (application-level: vllm, etc.)
    if artifact_paths.PROMETHEUS_UWM_DUMP_DIR is not None:
        db_files["uwm"] = (str(artifact_paths.PROMETHEUS_UWM_DUMP_DIR / "prometheus.t*"), get_llmd_uwm_metrics())

    if not db_files:
        logging.info("No Prometheus DB directories found, skipping metrics extraction")
        return None

    return helpers_store_parsers.extract_metrics(dirname, db_files)


SUTEST_CONTAINER_LABELS = [
    {"LLM Inference Service": dict(namespace="llm-d-project", pod=".*-kserve-.*")},
    {"LLM Inference Gateway": dict(namespace="llm-d-project", pod=".*-epp-.*")},
]

SUTEST_CONTAINER_EXTRA_METRICS_NAMES = [
    "LLM Inference Service",
    "LLM Inference Gateway",
]

def get_llmd_main_metrics(register=False):
    """Define the list of main Prometheus metrics to extract for LLM-D inference workloads"""

    cluster_role = "sutest"

    all_metrics = []

    all_metrics += [{"up": "up"}] # for the test start/end timestamp

    all_metrics += helper_prom_store.get_cluster_metrics(
        cluster_role, register=register,
        container_labels=SUTEST_CONTAINER_LABELS,
        gpu_container="main",
        network_metrics_names=SUTEST_CONTAINER_EXTRA_METRICS_NAMES,
    )

    return all_metrics


def get_llmd_uwm_metrics():
    """Define the list of UWM Prometheus metrics to extract for LLM-D inference workloads"""

    # Base metrics - always include 'up' for timestamp reference
    all_metrics = []
    all_metrics += [{"up": "up"}]  # for the test start/end timestamp

    # =============================================================================
    # 🔥 APPLICATION-LEVEL VLLM METRICS (stored in UWM Prometheus)
    # =============================================================================

    # End-to-end request latency (most critical for user experience)
    all_metrics += [
        {"vllm_e2e_latency_seconds_bucket": "kserve_vllm:e2e_request_latency_seconds_bucket"},
        {"vllm_e2e_latency_seconds_sum": "kserve_vllm:e2e_request_latency_seconds_sum"},
        {"vllm_e2e_latency_seconds_count": "kserve_vllm:e2e_request_latency_seconds_count"},
    ]

    # Time to First Token (TTFT) - critical for streaming response feel
    all_metrics += [
        {"vllm_ttft_seconds_bucket": "kserve_vllm:time_to_first_token_seconds_bucket"},
        {"vllm_ttft_seconds_sum": "kserve_vllm:time_to_first_token_seconds_sum"},
        {"vllm_ttft_seconds_count": "kserve_vllm:time_to_first_token_seconds_count"},
    ]

    # Inter-token latency - streaming quality
    all_metrics += [
        {"vllm_inter_token_latency_seconds_bucket": "kserve_vllm:inter_token_latency_seconds_bucket"},
        {"vllm_inter_token_latency_seconds_sum": "kserve_vllm:inter_token_latency_seconds_sum"},
        {"vllm_inter_token_latency_seconds_count": "kserve_vllm:inter_token_latency_seconds_count"},
    ]

    # Request processing phases
    all_metrics += [
        {"vllm_request_prefill_time_seconds_bucket": "kserve_vllm:request_prefill_time_seconds_bucket"},
        {"vllm_request_prefill_time_seconds_sum": "kserve_vllm:request_prefill_time_seconds_sum"},
        {"vllm_request_prefill_time_seconds_count": "kserve_vllm:request_prefill_time_seconds_count"},

        {"vllm_request_decode_time_seconds_bucket": "kserve_vllm:request_decode_time_seconds_bucket"},
        {"vllm_request_decode_time_seconds_sum": "kserve_vllm:request_decode_time_seconds_sum"},
        {"vllm_request_decode_time_seconds_count": "kserve_vllm:request_decode_time_seconds_count"},

        {"vllm_request_queue_time_seconds_bucket": "kserve_vllm:request_queue_time_seconds_bucket"},
        {"vllm_request_queue_time_seconds_sum": "kserve_vllm:request_queue_time_seconds_sum"},
        {"vllm_request_queue_time_seconds_count": "kserve_vllm:request_queue_time_seconds_count"},
    ]

    # Token throughput metrics - key performance indicators
    all_metrics += [
        {"vllm_prompt_tokens_total": "kserve_vllm:prompt_tokens_total"},
        {"vllm_generation_tokens_total": "kserve_vllm:generation_tokens_total"},
        {"vllm_request_prompt_tokens_bucket": "kserve_vllm:request_prompt_tokens_bucket"},
        {"vllm_request_generation_tokens_bucket": "kserve_vllm:request_generation_tokens_bucket"},
        {"vllm_request_max_num_generation_tokens_bucket": "kserve_vllm:request_max_num_generation_tokens_bucket"},
        {"vllm_request_max_num_generation_tokens_sum": "kserve_vllm:request_max_num_generation_tokens_sum"},
        {"vllm_request_max_num_generation_tokens_count": "kserve_vllm:request_max_num_generation_tokens_count"},
    ]

    # Request queue state and capacity
    all_metrics += [
        {"vllm_num_requests_running": "kserve_vllm:num_requests_running"},
        {"vllm_num_requests_waiting": "kserve_vllm:num_requests_waiting"},
        {"vllm_kv_cache_usage_perc": "kserve_vllm:kv_cache_usage_perc"},
        {"vllm_request_success_total": "kserve_vllm:request_success_total"},
    ]

    # =============================================================================
    # 🔧 COMPUTED VLLM METRICS (rate, average, increase transformations)
    # =============================================================================

    # E2E Request Latency computed metrics
    all_metrics += [
        {"vllm_e2e_latency_average": "rate(kserve_vllm:e2e_request_latency_seconds_sum[5m]) / rate(kserve_vllm:e2e_request_latency_seconds_count[5m])"},
        {"vllm_e2e_request_rate": "rate(kserve_vllm:e2e_request_latency_seconds_count[5m])"},
    ]

    # TTFT computed metrics
    all_metrics += [
        {"vllm_ttft_average": "rate(kserve_vllm:time_to_first_token_seconds_sum[5m]) / rate(kserve_vllm:time_to_first_token_seconds_count[5m])"},
        {"vllm_ttft_rate": "rate(kserve_vllm:time_to_first_token_seconds_count[5m])"},
    ]

    # Inter-token latency computed metrics
    all_metrics += [
        {"vllm_inter_token_average": "rate(kserve_vllm:inter_token_latency_seconds_sum[5m]) / rate(kserve_vllm:inter_token_latency_seconds_count[5m])"},
        {"vllm_inter_token_rate": "rate(kserve_vllm:inter_token_latency_seconds_count[5m])"},
    ]

    # Request processing phase computed metrics
    all_metrics += [
        {"vllm_prefill_average": "rate(kserve_vllm:request_prefill_time_seconds_sum[5m]) / rate(kserve_vllm:request_prefill_time_seconds_count[5m])"},
        {"vllm_prefill_rate": "rate(kserve_vllm:request_prefill_time_seconds_sum[5m])"},
        {"vllm_decode_average": "rate(kserve_vllm:request_decode_time_seconds_sum[5m]) / rate(kserve_vllm:request_decode_time_seconds_count[5m])"},
        {"vllm_decode_rate": "rate(kserve_vllm:request_decode_time_seconds_sum[5m])"},
        {"vllm_queue_average": "rate(kserve_vllm:request_queue_time_seconds_sum[5m]) / rate(kserve_vllm:request_queue_time_seconds_count[5m])"},
        {"vllm_queue_rate": "rate(kserve_vllm:request_queue_time_seconds_sum[5m])"},
    ]

    # Token throughput computed metrics
    all_metrics += [
        {"vllm_prompt_tokens_rate": "rate(kserve_vllm:prompt_tokens_total[5m])"},
        {"vllm_generation_tokens_rate": "rate(kserve_vllm:generation_tokens_total[5m])"},
        {"vllm_total_tokens_rate": "rate(kserve_vllm:prompt_tokens_total[5m]) + rate(kserve_vllm:generation_tokens_total[5m])"},
        {"vllm_avg_max_gen_tokens": "rate(kserve_vllm:request_max_num_generation_tokens_sum[5m]) / rate(kserve_vllm:request_max_num_generation_tokens_count[5m])"},
    ]

    # Request success computed metrics
    all_metrics += [
        {"vllm_request_success_rate": "rate(kserve_vllm:request_success_total[5m])"},
        {"vllm_request_success_increase": "increase(kserve_vllm:request_success_total[5m])"},
    ]

    return all_metrics
