from __future__ import annotations

import datetime
import pathlib

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, constr


import matrix_benchmarking.models as matbench_models


class PipelinesScaleMetadata(matbench_models.Metadata):
    settings: Dict[str, str]
    ocp_version: matbench_models.SemVer
    rhods_version: matbench_models.SemVer
    config: BaseModel


class PipelinesScaleResults(matbench_models.ExclusiveModel):
    results: BaseModel


class FromLocalEnv(BaseModel):
    artifacts_basedir: pathlib.Path
    source_url: Union[str, pathlib.Path, None]
    is_interactive: bool


class NodeItem(BaseModel):
    name: str
    sutest_cluster: bool
    managed: bool
    instance_type: str
    control_plane: bool
    rhods_compute: bool
    test_pods_only: bool
    infra: bool


class RhodsClusterInfo(BaseModel):
    node_count: List[NodeItem]
    control_plane: List[NodeItem]
    infra: List[NodeItem]
    rhods_compute: List[NodeItem]
    test_pods_only: List[NodeItem]


class RhodsInfo(BaseModel):
    version: str
    createdAt_raw: str
    createdAt: datetime.datetime


class UserDataEntry(BaseModel):
    artifact_dir: pathlib.Path
    exit_code: int
    progress: Dict[str, datetime.datetime]


class TesterJob(BaseModel):
    creation_time: datetime.datetime
    completion_time: datetime.datetime
    env: Dict[str, str]


class MetricEntry(BaseModel):
    metric: Dict[str, str]
    values: List[List[Union[int, str]]]


class Metrics(BaseModel):
    sutest: Dict[str, List[MetricEntry]]
    driver: Dict[str, List[MetricEntry]]


class ParsedResultsModel(BaseModel):
    parser_version: str
    artifacts_version: str
    from_local_env: FromLocalEnv
    user_count: int
    nodes_info: Dict[str, NodeItem]
    rhods_cluster_info: RhodsClusterInfo
    sutest_ocp_version: str
    rhods_info: RhodsInfo
    success_count: int
    user_data: Dict[int, UserDataEntry]
    tester_job: TesterJob
    metrics: Metrics
    test_config: Any

ParsedResultsModel.update_forward_refs()
TesterJob.update_forward_refs()
