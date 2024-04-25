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


class Metrics(matbench_models.ExclusiveModel):
    control_plane_node_cpu_idle: matbench_models.PrometheusValues = \
        Field(..., alias="Sutest Control Plane Node CPU idle")
    control_plane_node_cpu_usage: matbench_models.PrometheusValues = \
        Field(..., alias="Sutest Control Plane Node CPU usage")
    api_server_request_server_errors: matbench_models.PrometheusValues = \
        Field(..., alias="Sutest API Server Requests (server errors)")


class Results(matbench_models.ExclusiveModel):
    skeleton_results: bool
    metrics: Metrics


class SkeletonKPI(matbench_models.KPI, Settings): pass

SkeletonKPIs = matbench_models.getKPIsModel("SkeletonKPIs", __name__, kpi.KPIs, SkeletonKPI)

class Payload(matbench_models.ExclusiveModel):
    metadata: Metadata
    results: Results
    kpis: SkeletonKPIs
