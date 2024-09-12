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

    accelerator_type: str
    accelerator_count: int

    model_name: str
    tuning_method: str
    batch_size: int
    max_seq_length: int
    container_image: str

    replicas: int
    accelerators_per_replica: int

    lora_rank: Optional[int]
    lora_dropout: Optional[float]
    lora_alpha: Optional[int]
    lora_modules: Optional[str]

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
    train_tokens_per_second: float
    dataset_tokens_per_second: float
    gpu_hours_per_million_tokens: float
    dataset_tokens_per_second_per_gpu: float
    train_tokens_per_gpu_per_second: float
    train_samples_per_second: float
    train_runtime: float
    train_steps_per_second: float
    avg_tokens_per_sample: float

class KPI(matbench_models.KPI, Settings): pass

KPIs = matbench_models.getKPIsModel("KPIs", __name__, kpi.KPIs, KPI)

class Payload(matbench_models.ExclusiveModel):
    metadata: Metadata
    results: Results
    kpis: KPIs
