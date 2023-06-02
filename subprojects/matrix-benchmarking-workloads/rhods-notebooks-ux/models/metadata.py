from . import user

from typing import List, Dict

import matrix_benchmarking.models as models

from pydantic import BaseModel, constr


class NotebookScaleSettings(BaseModel):
    repeat: str
    test_case: str
    user_count: int
    exclude_tags: str
    version: models.SemVer


class InfraInfo(BaseModel):
    name: str
    infra: bool
    managed: bool
    control_plane: bool
    instance_type: str
    rhods_compute: bool
    sutest_cluster: bool
    test_pods_only: bool


class ClusterInfo(BaseModel):
    infra: List[InfraInfo]
    node_count: List[InfraInfo]
    control_plane: List[InfraInfo]
    rhods_compute: List[InfraInfo]
    test_pods_only: List[InfraInfo]
