from __future__ import annotations

from typing import Any, List, Optional

from pydantic import BaseModel, Field

import matrix_benchmarking.models as matbench_models


class Metadata(matbench_models.Metadata):
    presets: List[str]
    config: Any
    ocp_version: matbench_models.SemVer
    rhods_version: matbench_models.SemVer

class Results(matbench_models.ExclusiveModel):
    throughput: float
    time_per_output_token: List[float]
    time_to_first_token: List[float]
    model_load_duration: float

class Payload(matbench_models.ExclusiveModel):
    metadata: Metadata
    results: Results
