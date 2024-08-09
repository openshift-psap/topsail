from __future__ import annotations

from typing import Any, List, Optional

from pydantic import BaseModel, Field

import matrix_benchmarking.models as matbench_models
from . import kpi

KPI_SETTINGS_VERSION = "1.0"
class Settings(matbench_models.ExclusiveModel):
    kpi_settings_version: str

    ######?
    ocp_version: matbench_models.SemVer
    rhoai_version: matbench_models.SemVer
    instance_type: str

    accelerator_type: str
    accelerator_count: int

    model_name: str
    tuning_method: str
    batch_size: int
    max_seq_length: int
    container_image: str

    ci_engine: str
    run_id: str
    test_path: str
    urls: Optional[dict[str, str]]

    ######?




LTS_SCHEMA_VERSION = "1.0"
class Metadata(matbench_models.Metadata):
    lts_schema_version: str
    settings: Settings

    presets: List[str]
    config: str

class Results(matbench_models.ExclusiveModel):

    ######
    overall_accuracy: float
    #total_evaluation_time_seconds: float
    group_accuracies: dict

class KPI(matbench_models.KPI, Settings): pass

KPIs = matbench_models.getKPIsModel("KPIs", __name__, kpi.KPIs, KPI)

class Payload(matbench_models.ExclusiveModel):
    metadata: Metadata
    results: Results
    kpis: KPIs
