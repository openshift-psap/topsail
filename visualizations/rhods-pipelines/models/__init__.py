from __future__ import annotations

import datetime
import pathlib

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, constr
import pydantic

import matrix_benchmarking.models as matbench_models

class PipelinesScaleMetadata(matbench_models.Metadata, metaclass=matbench_models.AllOptional):
    settings: Dict[str, str]
    ocp_version: matbench_models.SemVer
    rhods_version: matbench_models.SemVer
    config: BaseModel


class PipelinesScaleResults(matbench_models.ExclusiveModel, metaclass=matbench_models.AllOptional):
    results: BaseModel


class FromLocalEnv(matbench_models.ExclusiveModel, metaclass=matbench_models.AllOptional):
    artifacts_basedir: pathlib.Path
    source_url: Union[str, pathlib.Path, None]
    is_interactive: bool


class NodeItem(matbench_models.ExclusiveModel, metaclass=matbench_models.AllOptional):
    name: str
    sutest_cluster: bool
    managed: bool
    instance_type: str
    control_plane: bool
    rhods_compute: bool
    test_pods_only: bool
    infra: bool


class RhodsClusterInfo(matbench_models.ExclusiveModel, metaclass=matbench_models.AllOptional):
    node_count: List[NodeItem]
    control_plane: List[NodeItem]
    infra: List[NodeItem]
    rhods_compute: List[NodeItem]
    test_pods_only: List[NodeItem]


class RhodsInfo(matbench_models.ExclusiveModel, metaclass=matbench_models.AllOptional):
    version: str
    createdAt_raw: str
    createdAt: datetime.datetime
    full_version: str


class PodTime(matbench_models.ExclusiveModel, metaclass=matbench_models.AllOptional):
    pod_name: str
    pod_friendly_name: str
    pod_namespace: str
    hostname: Union[str, None] # missing if the Pod is still Pending

    creation_time: datetime.datetime
    start_time: Union[datetime.datetime, None] # missing if the Pod is still Pending
    containers_ready: Union[datetime.datetime, None]
    pod_initialized: Union[datetime.datetime, None]
    pod_scheduled: Union[datetime.datetime, None]
    container_finished: Union[datetime.datetime, None] # missing if the Pod is still Running

    is_dspa: bool = Field(default_factory=lambda: False)
    is_pipeline_task: bool = Field(default_factory=lambda: False)


class UserDataEntry(matbench_models.ExclusiveModel, metaclass=matbench_models.AllOptional):
    artifact_dir: pathlib.Path
    exit_code: int
    progress: Dict[str, datetime.datetime]
    resource_times: Dict[str, datetime.datetime]
    pod_times: List[PodTime]

class TesterJob(matbench_models.ExclusiveModel, metaclass=matbench_models.AllOptional):
    creation_time: datetime.datetime
    completion_time: datetime.datetime
    env: Dict[str, str]


class MetricEntry(matbench_models.ExclusiveModel, metaclass=matbench_models.AllOptional):
    metric: Dict[str, str]
    values: List[List[Union[int, str]]]


class Metrics(matbench_models.ExclusiveModel, metaclass=matbench_models.AllOptional):
    sutest: matbench_models.PrometheusNamedMetricValues
    driver: matbench_models.PrometheusNamedMetricValues


class ParsedResultsModel(matbench_models.ExclusiveModel, metaclass=matbench_models.AllOptional):
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
