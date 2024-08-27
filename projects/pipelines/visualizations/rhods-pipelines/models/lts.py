from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

import matrix_benchmarking.models as matbench_models
from .. import models as pipelines_models

from . import kpi

KPI_SETTINGS_VERSION = "1.0"
class Settings(matbench_models.ExclusiveModel):
    kpi_settings_version: str

    instance_type: str

    ocp_version: matbench_models.SemVer
    rhoai_version: matbench_models.SemVer

    ci_engine: str
    run_id: str
    test_path: str
    urls: Optional[dict[str, str]]


LTS_SCHEMA_VERSION = "1.1"
# 1.1: add lts_schema_version and KPIs
# 1.0: base version, no lts_schema_version setting

class Metadata(matbench_models.Metadata):
    lts_schema_version: str
    presets: List[str]

    settings: Settings

    ocp_version: matbench_models.SemVer
    rhods_version: matbench_models.SemVer
    user_count: int
    config: str


class SutestMetrics(matbench_models.ExclusiveModel):
    control_plane_node_cpu_idle: matbench_models.PrometheusValues = Field(..., alias="Sutest Control Plane Node CPU idle")
    control_plane_node_cpu_usage: matbench_models.PrometheusValues = Field(..., alias="Sutest Control Plane Node CPU usage")
    api_server_request_server_errors: matbench_models.PrometheusValues = Field(..., alias="Sutest API Server Requests (server errors)")


class Metrics(matbench_models.ExclusiveModel):
    sutest: SutestMetrics


class Results(matbench_models.ExclusiveModel): pass


class KPI(matbench_models.KPI, Settings): pass

KPIs = matbench_models.getKPIsModel("KPIs", __name__, kpi.KPIs, KPI)


class Payload(matbench_models.ExclusiveModel):
    metadata: Metadata
    results: Results

    kpis: Optional[KPIs]
