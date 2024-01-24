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


class Metadata(matbench_models.Metadata):
    presets: List[str]
    rhods_version: str
    ocp_version: str
    test: str
    config: Any


class BenchmarkMeasures(matbench_models.ExclusiveModel):
    benchmark: str
    repeat: int
    number: int
    measures: List[float]


class Results(matbench_models.ExclusiveModel):
    benchmark_measures: BenchmarkMeasures

NotebookPerformanceKPIs = matbench_models.getKPIsModel("NotebookPerformanceKPIs", __name__, kpi.KPIs, kpi.NotebookPerformanceKPI)

class Payload(matbench_models.ExclusiveModel):
    schema_name: matbench_models.create_schema_field("rhods-notebooks-perf") = Field(alias="$schema")
    metadata: Metadata
    results: Results
    kpis: Optional[NotebookPerformanceKPIs]
    regression_results: Optional[Any]

    class Config:
        fields = {'schema_name': '$schema'}
