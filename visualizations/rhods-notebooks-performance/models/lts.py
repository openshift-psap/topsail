from __future__ import annotations

from typing import List, Union, Any

from pydantic import BaseModel

import matrix_benchmarking.models as matbench_models

class Metadata(matbench_models.Metadata):
    presets: List[str]
    rhods_version: str
    ocp_version: str
    config: Any

class BenchmarkMeasures(BaseModel):
    benchmark: str
    repeat: int
    number: int
    measures: List[float]


class Results(BaseModel):
    benchmark_measures: BenchmarkMeasures


class Payload(BaseModel):
    metadata: Metadata
    results: Results
