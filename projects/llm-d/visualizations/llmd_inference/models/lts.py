from __future__ import annotations

from typing import Any, List, Optional, Dict

from pydantic import BaseModel, Field

import matrix_benchmarking.models as matbench_models
from . import kpi

KPI_SETTINGS_VERSION = "1.0"

class Settings(BaseModel):
    kpi_settings_version: str = KPI_SETTINGS_VERSION

    # Allow any extra fields without validation
    class Config:
        extra = "allow"

class MultiturnBenchmark(matbench_models.ExclusiveModel):
    total_time: float
    total_requests: int
    completed_conversations: int
    total_conversations: int
    requests_per_second: float

    # Time to First Token (TTFT) metrics
    ttft_min: float
    ttft_max: float
    ttft_mean: float
    ttft_p50: float
    ttft_p95: float
    ttft_p99: float

    # Total Request Time metrics
    total_request_time_min: float
    total_request_time_max: float
    total_request_time_mean: float
    total_request_time_p50: float
    total_request_time_p95: float

    # TTFT by turn number and document type
    ttft_by_turn: Dict[int, float] = Field(default_factory=dict)
    ttft_by_doc_type: Dict[str, float] = Field(default_factory=dict)

    # First turn vs subsequent turns
    first_turn_avg: Optional[float] = None
    later_turns_avg: Optional[float] = None
    speedup_ratio: Optional[float] = None

class GuidellmBenchmark(matbench_models.ExclusiveModel):
    strategy: str
    duration: float
    warmup_time: float
    cooldown_time: float

    # Request metrics
    request_rate: float
    request_concurrency: float
    completed_requests: int
    failed_requests: int

    # Token metrics (per request)
    input_tokens_per_request: float
    output_tokens_per_request: float
    total_tokens_per_request: float

    # Latency metrics
    request_latency_median: float
    request_latency_p95: float
    ttft_median: float
    ttft_p95: float
    itl_median: float  # Inter Token Latency
    itl_p95: float
    tpot_median: float  # Time Per Output Token
    tpot_p95: float

    # Throughput metrics
    tokens_per_second: float
    input_tokens_per_second: float
    output_tokens_per_second: float

LTS_SCHEMA_VERSION = "1.0"

class Metadata(matbench_models.Metadata):
    lts_schema_version: str
    settings: Settings
    presets: List[str] = Field(default_factory=list)

class Results(matbench_models.ExclusiveModel):
    # Test metadata
    test_name: str
    test_success: bool = True
    test_failure_reason: Optional[str] = None

    # Benchmark results
    multiturn_benchmark: Optional[MultiturnBenchmark] = None
    guidellm_benchmarks: List[GuidellmBenchmark] = Field(default_factory=list)

    # Raw data paths for reference
    multiturn_log_path: Optional[str] = None
    guidellm_log_path: Optional[str] = None
    prometheus_path: Optional[str] = None

class LlmdInferenceKPI(matbench_models.KPI, Settings):
    pass

LlmdInferenceKPIs = matbench_models.getKPIsModel("LlmdInferenceKPIs", __name__, kpi.KPIs, LlmdInferenceKPI)

class Payload(matbench_models.ExclusiveModel):
    metadata: Metadata
    results: Results
    kpis: Optional[LlmdInferenceKPIs] = None
