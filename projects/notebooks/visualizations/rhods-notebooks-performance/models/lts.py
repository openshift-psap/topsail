from __future__ import annotations

from typing import List, Union, Any, Optional

import pydantic
from pydantic import BaseModel, Field

import matrix_benchmarking.models as matbench_models
from . import kpi


#
# VERSION must be bumped after every model or PKI update
#
VERSION = "1.0.0"

class Settings(matbench_models.ExclusiveModel):
    rhoai_version: matbench_models.SemVer
    ocp_version: matbench_models.SemVer
    image: str
    image_tag: str
    image_name: str
    instance_type: str
    benchmark_name: str
    test_flavor: str
    ci_engine: str


class Metadata(matbench_models.Metadata):
    settings: Settings
    presets: List[str]
    rhods_version: str
    ocp_version: str
    test: str
    config: Any

    ci_engine: str = Field(default="Not set")
    run_id: str = Field(default="Not set")
    test_path: str = Field(default="Not set")
    urls: Optional[dict[str, str]]


class BenchmarkMeasures(matbench_models.ExclusiveModel):
    benchmark: str
    repeat: int
    number: int
    measures: List[float]


class Results(matbench_models.ExclusiveModel):
    benchmark_measures: BenchmarkMeasures
    regression: NotebookPerformanceRegression

class NotebookPerformanceKPI(matbench_models.KPI, Settings): pass


NotebookPerformanceKPIs = matbench_models.getKPIsModel("NotebookPerformanceKPIs", __name__, kpi.KPIs, NotebookPerformanceKPI)
NotebookPerformanceRegression = matbench_models.RegressionResult

class Payload(matbench_models.ExclusiveModel):
    schema_name: matbench_models.create_schema_field("rhods-notebooks-perf") = Field(alias="$schema")
    metadata: Metadata
    results: Results
    kpis: Optional[NotebookPerformanceKPIs]

    class Config:
        fields = {'schema_name': '$schema'}
