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


class FromLocalEnv(matbench_models.ExclusiveModel):
    artifacts_basedir: pathlib.Path
    source_url: Union[str, pathlib.Path, None]
    is_interactive: bool


class NodeItem(matbench_models.ExclusiveModel):
    name: str
    sutest_cluster: bool
    managed: bool
    instance_type: str
    control_plane: bool
    rhods_compute: bool
    test_pods_only: bool
    infra: bool


class RhodsClusterInfo(matbench_models.ExclusiveModel):
    node_count: List[NodeItem]
    control_plane: List[NodeItem]
    infra: List[NodeItem]
    rhods_compute: List[NodeItem]
    test_pods_only: List[NodeItem]


class RhodsInfo(matbench_models.ExclusiveModel):
    version: str
    createdAt_raw: str
    createdAt: datetime.datetime
    full_version: str

class UserDataEntry(matbench_models.ExclusiveModel):
    artifact_dir: pathlib.Path
    exit_code: int
    progress: Dict[str, datetime.datetime]


class TesterJob(matbench_models.ExclusiveModel):
    creation_time: datetime.datetime
    completion_time: datetime.datetime
    env: Dict[str, str]


class MetricEntry(matbench_models.ExclusiveModel):
    metric: Dict[str, str]
    values: List[List[Union[int, str]]]


class Metrics(matbench_models.ExclusiveModel):
    sutest: matbench_models.PrometheusNamedMetricValues
    driver: matbench_models.PrometheusNamedMetricValues


class PodTime(matbench_models.ExclusiveModel):
    user_index: int
    pod_name: str
    pod_namespace: str
    hostname: Union[str, None] # missing if the Pod is still Pending

    start_time: Union[datetime.datetime, None] # missing if the Pod is still Pending
    containers_ready: Union[datetime.datetime, None]
    pod_initialized: Union[datetime.datetime, None]
    pod_scheduled: Union[datetime.datetime, None]
    container_finished: Union[datetime.datetime, None] # missing if the Pod is still Running


class ParsedResultsModel(matbench_models.ExclusiveModel):
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
    pod_times: List[PodTime]

ParsedResultsModel.update_forward_refs()
TesterJob.update_forward_refs()
