from . import user

from typing import List, Dict

import matrix_benchmarking.models as matbench_models

from pydantic import BaseModel, constr


class InfraInfo(matbench_models.ExclusiveModel):
    name: str
    infra: bool
    managed: bool
    control_plane: bool
    instance_type: str
    rhods_compute: bool
    sutest_cluster: bool
    test_pods_only: bool


class ClusterInfo(matbench_models.ExclusiveModel):
    infra: List[InfraInfo]
    node_count: List[InfraInfo]
    control_plane: List[InfraInfo]
    rhods_compute: List[InfraInfo]
    test_pods_only: List[InfraInfo]
