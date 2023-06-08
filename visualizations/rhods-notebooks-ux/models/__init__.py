from . import user, metadata

from typing import List, Dict

import matrix_benchmarking.models as matbench_models

from pydantic import BaseModel, constr

class NotebookScaleMetadata(matbench_models.Metadata):
    test: enums.TestName
    cluster_info: metadata.ClusterInfo
    settings: metadata.NotebookScaleSettings


class NotebookScaleData(matbench_models.ExclusiveModel):
    users: List[user.UserData]
    config: BaseModel
    metrics: Dict[str, matbench_models.PrometheusMetric]
    thresholds: BaseModel
    ocp_version: matbench_models.SemVer
    rhods_version: matbench_models.SemVer


class NotebookScalePayload(matbench_models.create_PSAPPayload('rhods-matbench-upload')):
    data: NotebookScaleData
    metadata: NotebookScaleMetadata
