from __future__ import annotations

from typing import Any, List, Optional

from pydantic import BaseModel, Field

import matrix_benchmarking.models as matbench_models
from . import kpi

KPI_SETTINGS_VERSION = "1.0"
class Settings(matbench_models.ExclusiveModel):
    kpi_settings_version: str
    ocp_version: matbench_models.SemVer
    rhoai_version: matbench_models.SemVer
    instance_type: str

    container_image: str

    accelerator_type: str
    accelerator_count: int

    replicas: int
    accelerators_per_replica: int

    model_name: str
    max_batch_len: int
    num_epochs: int
    cpu_offload: bool

    dataset_name: str

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
    average_throughput: float


class KPI(matbench_models.KPI, Settings): pass

KPIs = matbench_models.getKPIsModel("KPIs", __name__, kpi.KPIs, KPI)

class Payload(matbench_models.ExclusiveModel):
    metadata: Metadata
    results: Results
    kpis: KPIs
