from __future__ import annotations

from typing import Any, List, Optional

from pydantic import BaseModel, Field

import matrix_benchmarking.models as matbench_models

from . import ilab_kpi as kpi

KPI_SETTINGS_VERSION = "1.2"
# 1.2: expose more labels, to match the fine_tuning KPI labels
# 1.1: expose more KPIs
# 1.0: first version
#

class Settings(matbench_models.ExclusiveModel):
    kpi_settings_version: str
    ocp_version: matbench_models.SemVer
    rhoai_version: matbench_models.SemVer
    instance_type: str

    accelerator_name: str
    accelerator_count: Optional[int]

    model_name: Optional[str]
    container_image: Optional[str]

    replicas: Optional[int]
    accelerators_per_replica: Optional[int]

    dataset_name: Optional[str]

    ci_engine: str
    run_id: str
    test_path: str
    urls: Optional[dict[str, str]]


class GpuMetadata(matbench_models.ExclusiveModel):
    product: str
    memory: float
    count: int


LTS_SCHEMA_VERSION = "1.0"
class Metadata(matbench_models.Metadata):
    lts_schema_version: str

    settings: Settings

    presets: List[str]
    config: str
    gpus: List[GpuMetadata]


class Metrics(matbench_models.ExclusiveModel):
    network_total_usage: matbench_models.PrometheusValues = Field(..., alias="sutest__container_network_transmit_bytes_total__namespace=fine-tuning-testing")

    # py_field_name: matbench_models.PrometheusValues = Field(..., alias="<metric description name>")


class Results(matbench_models.ExclusiveModel):
    metrics: Metrics


class KPI(matbench_models.KPI, Settings): pass

KPIs = matbench_models.getKPIsModel("KPIs", __name__, kpi.KPIs, KPI)


class Payload(matbench_models.ExclusiveModel):
    metadata: Metadata
    results: Results
    kpis: Optional[KPIs]
