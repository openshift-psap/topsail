from __future__ import annotations

from typing import Any, List, Optional

from pydantic import BaseModel, Field

import matrix_benchmarking.models as matbench_models


class Metadata(matbench_models.Metadata):
    presets: List[str]
    config: Any
    ocp_version: matbench_models.SemVer

class Metrics(matbench_models.ExclusiveModel):
    control_plane_node_cpu_idle: matbench_models.PrometheusValues = \
        Field(..., alias="Sutest Control Plane Node CPU idle")
    control_plane_node_cpu_usage: matbench_models.PrometheusValues = \
        Field(..., alias="Sutest Control Plane Node CPU usage")
    api_server_request_server_errors: matbench_models.PrometheusValues = \
        Field(..., alias="Sutest API Server Requests (server errors)")


class Results(matbench_models.ExclusiveModel):
    skeleton_results: bool
    metrics: Metrics


class Payload(matbench_models.ExclusiveModel):
    metadata: Metadata
    results: Results
