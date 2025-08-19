from __future__ import annotations

from typing import Any, List, Optional

from pydantic import BaseModel, Field
from enum import Enum

import matrix_benchmarking.models as matbench_models
from . import kpi

KPI_SETTINGS_VERSION = "1.1"
# 1.0: first version
# 1.1: switching from llm-load-test to llama-bench results

class Settings(matbench_models.ExclusiveModel):
    kpi_settings_version: str

    model_name: str
    platform: str
    version: str
    containerized: bool
    hardware: str
    os: str
    urls: Optional[dict[str, str]]


class LlmLoadTestStats(matbench_models.ExclusiveModel):
    values: List[float]
    min: float
    max: float
    median: float
    mean: float
    percentile_80: float
    percentile_90: float
    percentile_95: float
    percentile_99: float

class LlamaBenchStats(matbench_models.ExclusiveModel):
    throughput: float
    err: float

LTS_SCHEMA_VERSION = "1.1"
# 1.0: first version
# 1.1: switching from llm-load-test to llama-bench results

class Metadata(matbench_models.Metadata):
    lts_schema_version: str

    settings: Settings
    presets: List[str]

    ci_engine: str = Field(default="Not set")
    run_id: str = Field(default="Not set")
    test_path: str = Field(default="Not set")
    urls: Optional[dict[str, str]]


class Results(matbench_models.ExclusiveModel):
    streaming: bool
    throughput: float
    time_per_output_token: LlmLoadTestStats
    inter_token_latency: Optional[LlmLoadTestStats]
    time_to_first_token: Optional[LlmLoadTestStats]
    model_load_duration: Optional[float]
    failures: int

    prompt_processing: LlamaBenchStats
    token_generation: LlamaBenchStats


class KPI(matbench_models.KPI, Settings): pass

KPIs = matbench_models.getKPIsModel("KPIs", __name__, kpi.KPIs, KPI)

class Payload(matbench_models.ExclusiveModel):
    metadata: Metadata
    results: Results
    kpis: Optional[KPIs]
