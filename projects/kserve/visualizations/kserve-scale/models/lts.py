from __future__ import annotations

from typing import Any, List, Optional

from pydantic import BaseModel, Field

import matrix_benchmarking.models as matbench_models


class Metadata(matbench_models.Metadata):
    presets: List[str]
    config: Any
    ocp_version: matbench_models.SemVer
    rhoai_version: matbench_models.SemVer

    number_of_inferenceservices_to_create: int
    number_of_inferenceservice_per_user: int
    number_of_users: int


class Results(matbench_models.ExclusiveModel):
    inferenceservice_load_times: List[float]
    number_of_inferenceservices_loaded: int
    number_of_successful_users: int
    test_duration: float


class Payload(matbench_models.ExclusiveModel):
    metadata: Metadata
    results: Results
