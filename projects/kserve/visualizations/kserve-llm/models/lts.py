from __future__ import annotations

from typing import Any, List, Optional

from pydantic import BaseModel, Field
from enum import Enum

import matrix_benchmarking.models as matbench_models
from . import kpi

class Settings(matbench_models.ExclusiveModel):
    instance_type: str
    accelerator_type: str
    accelerator_count: int
    accelerator_memory: int
    ocp_version: matbench_models.SemVer
    rhoai_version: matbench_models.SemVer
    deployment_mode: str
    model_name: str
    runtime_image: str
    min_pod_replicas: int
    max_pod_replicas: int
    virtual_users: int
    test_duration: int
    dataset_name: str
    mode: str

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

class Results(matbench_models.ExclusiveModel):
    throughput: float
    time_per_output_token: LlmLoadTestStats
    time_to_first_token: Optional[LlmLoadTestStats]
    model_load_duration: Optional[float]

class KServeLLMPerformanceKPI(matbench_models.KPI, Settings): pass

KServeLLMPerformanceKPIs = matbench_models.getKPIsModel("KServeLLMPerformanceKPIs", __name__, kpi.KPIs, KServeLLMPerformanceKPI)

class Payload(matbench_models.ExclusiveModel):
    metadata: Metadata
    results: Results
    kpis: Optional[KServeLLMPerformanceKPIs]
