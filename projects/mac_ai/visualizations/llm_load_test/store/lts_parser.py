import types
import logging
import pytz
import pathlib
import yaml

from .. import models
from ..models import lts as models_lts


def generate_lts_payload(results, import_settings):
    lts_payload = types.SimpleNamespace()

    lts_payload.metadata = generate_lts_metadata(results, import_settings)
    lts_payload.results = generate_lts_results(results)
    # lts_payload.kpis is generated in the helper store

    return lts_payload


def _generate_throughput(results):
    if not results.llm_load_test_output: return None

    return results.llm_load_test_output["summary"]["throughput"]


def _generate_time_per_output_token(results):
    if not results.llm_load_test_output: return None

    tpot = dict(results.llm_load_test_output["summary"]["tpot"])
    tpot["values"] = [x["tpot"] for x in results.llm_load_test_output["results"] if x["tpot"]]
    return types.SimpleNamespace(**tpot)


def _generate_inter_token_latency(results):
    if not results.llm_load_test_output: return None

    itl = dict(results.llm_load_test_output["summary"]["itl"])
    itl["values"] = [x["itl"] for x in results.llm_load_test_output["results"] if x["itl"]]
    return types.SimpleNamespace(**itl)


def _generate_time_to_first_token(results):
    if not results.llm_load_test_output: return None

    ttft = dict(results.llm_load_test_output["summary"]["ttft"])
    ttft["values"] = [x["ttft"] for x in results.llm_load_test_output["results"] if x["ttft"]]
    return types.SimpleNamespace(**ttft)


def _generate_failures(results):
    if not results.llm_load_test_output: return None

    return results.llm_load_test_output["summary"]["total_failures"]


def _is_streaming(results):
    return results.test_config.get("test.llm_load_test.args.streaming")


def generate_lts_settings(lts_metadata, results, import_settings):
    lts_settings = types.SimpleNamespace()

    lts_settings.kpi_settings_version = models_lts.KPI_SETTINGS_VERSION

    lts_settings.model_name = results.test_config.get("test.model.name")
    lts_settings.platform = results.test_config.get("test.platform")

    if "ramalama" in lts_settings.platform:
        version_config_key = "prepare.ramalama.repo.version"
        containerized = True
    elif "llama_cpp" in lts_settings.platform:
        version_config_key = "prepare.llama_cpp.release.repo.version" if "upstream_bin" in lts_settings.platform \
            else "prepare.llama_cpp.source.repo.version"

        containerized = "podman" in lts_settings.platform
    elif "ollama" in lts_settings.platform:
        version_config_key = "prepare.ollama.repo.version"
        containerized = False
    else:
        logging.error(f"Unknown platform '{lts_settings.platform}', cannot find the version.")
        version_config_key = None
        containerized = None

    lts_settings.version = results.test_config.get(version_config_key) \
        if version_config_key else "Unknown"

    if "ramalama" in lts_settings.platform and results.ramalama_commit_info:
        lts_settings.version = f"{lts_settings.version}-{results.ramalama_commit_info.date_id}"

    lts_settings.containerized = containerized

    lts_settings.hardware = ""
    try: lts_settings.hardware += results.system_state["Hardware"]["Hardware Overview"]["Chip"] + " "
    except Exception:
        logging.error("Couldn't find the system chip name")

    try: lts_settings.hardware += results.system_state["Hardware"]["Hardware Overview"]["Memory"] + " "
    except Exception:
        logging.error("Couldn't find the system memory")

    lts_settings.hardware = lts_settings.hardware.strip()
    if not lts_settings.hardware:
        lts_settings.hardware = "Unknown"

    try: lts_settings.os = results.system_state["Software"]["System Software Overview"]["System Version"].split(" (")[0]
    except Exception:
        logging.error("Couldn't find the system OS")
        lts_settings.os = "Unknown"

    lts_settings.urls = results.from_env.test.urls

    return lts_settings


def generate_lts_metadata(results, import_settings):

    lts_metadata = types.SimpleNamespace()

    start_time = None
    end_time = None

    if results.test_start_end:
        start_time = results.test_start_end.start
        end_time = results.test_start_end.end

        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=pytz.UTC)
        if end_time.tzinfo is None:
            end_time = end_time.replace(tzinfo=pytz.UTC)

    lts_metadata.start = start_time
    lts_metadata.end = end_time

    lts_metadata.lts_schema_version = models_lts.LTS_SCHEMA_VERSION
    lts_metadata.settings = generate_lts_settings(lts_metadata, results, dict(import_settings))

    lts_metadata.test_uuid = str(results.test_uuid)
    lts_metadata.urls = {}
    lts_metadata.presets = []


    return lts_metadata


def generate_lts_results(results):
    results_lts = types.SimpleNamespace()

    # Throughout value (scalar, in token/ms)
    results_lts.throughput = _generate_throughput(results)

    # Time Per Output Token value
    results_lts.time_per_output_token = _generate_time_per_output_token(results)

    results_lts.streaming = _is_streaming(results)

    if results_lts.streaming:
        # Inter Token Latency (ms)
        results_lts.inter_token_latency = _generate_inter_token_latency(results)

        # Time To First Token values for all of the calls (vector)
        results_lts.time_to_first_token = _generate_time_to_first_token(results)
    else:
        results_lts.inter_token_latency = None
        results_lts.time_to_first_token = None

    # Number of failures
    results_lts.failures = _generate_failures(results)

    return results_lts


def get_kpi_labels(lts_payload):

    kpi_labels = dict(lts_payload.metadata.settings.__dict__)
    kpi_labels["@timestamp"] = lts_payload.metadata.start.strftime('%Y-%m-%dT%H:%M:%S.%fZ') \
        if lts_payload.metadata.start else None

    kpi_labels["test_uuid"] = lts_payload.metadata.test_uuid


    return kpi_labels
