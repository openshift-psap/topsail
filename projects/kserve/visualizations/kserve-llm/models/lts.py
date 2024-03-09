from __future__ import annotations

from typing import Any, List, Optional

from pydantic import BaseModel, Field
from enum import Enum

import matrix_benchmarking.models as matbench_models
from . import kpi

class Settings(matbench_models.ExclusiveModel):
    instance_type: str
    accelerator_name: str

    ocp_version: matbench_models.SemVer
    rhoai_version: matbench_models.SemVer
    deployment_mode: str
    model_name: str
    runtime_image: str
    min_pod_replicas: int
    max_pod_replicas: Optional[int]
    virtual_users: int
    test_duration: int
    dataset_name: str
    test_mode: str
    streaming: bool

    ci_engine: str
    run_id: str
    test_path: str
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

class Metadata(matbench_models.Metadata):
    settings: Settings
    presets: List[str]
    config: Any
    ocp_version: matbench_models.SemVer
    rhods_version: matbench_models.SemVer

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

class KServeLLMPerformanceKPI(matbench_models.KPI, Settings): pass

KServeLLMPerformanceKPIs = matbench_models.getKPIsModel("KServeLLMPerformanceKPIs", __name__, kpi.KPIs, KServeLLMPerformanceKPI)

class Payload(matbench_models.ExclusiveModel):
    metadata: Metadata
    results: Results
    kpis: Optional[KServeLLMPerformanceKPIs]
