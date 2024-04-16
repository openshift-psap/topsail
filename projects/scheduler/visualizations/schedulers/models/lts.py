from __future__ import annotations

from typing import Any, List, Optional

from pydantic import BaseModel, Field

import matrix_benchmarking.models as matbench_models


class Metadata(matbench_models.Metadata):
    presets: List[str]
    config: Any
    ocp_version: matbench_models.SemVer


class Results(matbench_models.ExclusiveModel):
    last_launch_to_last_schedule_sec: float
    time_to_last_launch_sec: float
    time_to_last_schedule_sec: float
    time_to_test_sec: float

class Payload(BaseModel):
    metadata: Metadata
    results: Results
