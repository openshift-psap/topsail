from __future__ import annotations

from typing import Any, List, Optional

from pydantic import BaseModel, Field

import matrix_benchmarking.models as matbench_models

from . import kpi

KPI_SETTINGS_VERSION = "1.1"
class Settings(matbench_models.ExclusiveModel):
    kpi_settings_version: str

    ocp_version: matbench_models.SemVer
    rhoai_version: matbench_models.SemVer

    ci_engine: str
    run_id: str
    test_path: str
    urls: Optional[dict[str, str]]

    test_mode: str
    obj_count: int
    total_pod_count: int
    pod_runtime: int

    launch_duration: int


LTS_SCHEMA_VERSION = "1.0"
class Metadata(matbench_models.Metadata):
    lts_schema_version: str

    settings: Settings
    presets: List[str]
    config: Any


class Results(matbench_models.ExclusiveModel):
    last_launch_to_last_schedule_sec: float
    time_to_last_launch_sec: float
    time_to_last_schedule_sec: float
    time_to_test_sec: float


class KPI(matbench_models.KPI, Settings): pass

KPIs = matbench_models.getKPIsModel("KPIs", __name__, kpi.KPIs, KPI)

class Payload(BaseModel):
    metadata: Metadata
    results: Results
    kpis: Optional[KPIs]
