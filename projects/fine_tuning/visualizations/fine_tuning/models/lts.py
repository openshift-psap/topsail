from __future__ import annotations

from typing import Any, List, Optional

from pydantic import BaseModel, Field

import matrix_benchmarking.models as matbench_models
from . import kpi

KPI_SETTINGS_VERSION = "1.1"
class Settings(matbench_models.ExclusiveModel):
    kpi_settings_version: str
    ocp_version: matbench_models.SemVer

    ci_engine: str
    run_id: str
    test_path: str
    urls: Optional[dict[str, str]]


LTS_SCHEMA_VERSION = "1.0"
class Metadata(matbench_models.Metadata):
    lts_schema_version: str
    settings: Settings

    presets: List[str]
    config: str
    ocp_version: matbench_models.SemVer


class Results(matbench_models.ExclusiveModel):
    skeleton_results: bool


class SkeletonKPI(matbench_models.KPI, Settings): pass

SkeletonKPIs = matbench_models.getKPIsModel("SkeletonKPIs", __name__, kpi.KPIs, SkeletonKPI)

class Payload(matbench_models.ExclusiveModel):
    metadata: Metadata
    results: Results
    kpis: SkeletonKPIs
