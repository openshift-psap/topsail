from __future__ import annotations

from typing import Any, List, Optional

from pydantic import BaseModel, Field
from enum import Enum

import matrix_benchmarking.models as matbench_models
from . import kpi

KPI_SETTINGS_VERSION = "1.0"
# 1.0: first version

class Settings(matbench_models.ExclusiveModel):
    kpi_settings_version: str

    instance_type: str
    user_count: int
    run_count: int
    project_count: int
    run_delay: int
    user_pipeline_delay: int
    sleep_factor: int
    project_count: int
    notebook: str

    ocp_version: matbench_models.SemVer
    rhoai_version: matbench_models.SemVer

    ci_engine: str
    run_id: str
    test_path: str
    urls: Optional[dict[str, str]]


class DSPTestStats(matbench_models.ExclusiveModel):
    values: List[float]
    min: float
    max: float
    median: float
    mean: float
    percentile_80: float
    percentile_90: float
    percentile_95: float
    percentile_99: float
    degrade_speed: float


LTS_SCHEMA_VERSION = "1.0"
class Metadata(matbench_models.Metadata):
    lts_schema_version: str

    settings: Settings
    presets: List[str]
    config: str
    ocp_version: matbench_models.SemVer
    rhods_version: matbench_models.SemVer

    ci_engine: str = Field(default="Not set")
    run_id: str = Field(default="Not set")
    test_path: str = Field(default="Not set")
    urls: Optional[dict[str, str]]


class Results(matbench_models.ExclusiveModel):
    run_latency: DSPTestStats
    run_duration: DSPTestStats


class DSPPerformanceKPI(matbench_models.KPI, Settings): pass

DSPPerformanceKPIs = matbench_models.getKPIsModel("DSPPerformanceKPIs", __name__, kpi.KPIs, DSPPerformanceKPI)


class Payload(matbench_models.ExclusiveModel):
    metadata: Metadata
    results: Results
    kpis: Optional[DSPPerformanceKPIs]
