from __future__ import annotations

from typing import Any, List, Optional

from pydantic import BaseModel, Field

import matrix_benchmarking.models as matbench_models
from . import kpi

KPI_SETTINGS_VERSION = "1.0"
class Settings(matbench_models.ExclusiveModel):
    kpi_settings_version: str


LTS_SCHEMA_VERSION = "1.0"
class Metadata(matbench_models.Metadata):
    lts_schema_version: str
    settings: Settings

    presets: List[str]
    config: str

class Results(matbench_models.ExclusiveModel):
    pass

class KPI(matbench_models.KPI, Settings): pass

KPIs = matbench_models.getKPIsModel("KPIs", __name__, kpi.KPIs, KPI)

class Payload(matbench_models.ExclusiveModel):
    metadata: Metadata
    results: Results
    kpis: KPIs
