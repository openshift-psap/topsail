from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

import matrix_benchmarking.models as matbench_models
from .. import models as pipelines_models

class Metadata(matbench_models.Metadata):
    presets: List[str]

    ocp_version: matbench_models.SemVer
    rhods_version: matbench_models.SemVer
    user_count: int
    config: str

class SutestMetrics(matbench_models.ExclusiveModel):
    control_plane_node_cpu_idle: matbench_models.PrometheusValues = Field(..., alias="Sutest Control Plane Node CPU idle")
    control_plane_node_cpu_usage: matbench_models.PrometheusValues = Field(..., alias="Sutest Control Plane Node CPU usage")
    api_server_request_server_errors: matbench_models.PrometheusValues = Field(..., alias="Sutest API Server Requests (server errors)")

class Metrics(matbench_models.ExclusiveModel):
    sutest: SutestMetrics

class Results(matbench_models.ExclusiveModel): pass


class Payload(matbench_models.ExclusiveModel):
    metadata: Metadata
    results: Results
