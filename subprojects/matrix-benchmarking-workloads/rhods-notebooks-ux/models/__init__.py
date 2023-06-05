from . import user, metadata

from typing import List, Dict

import matrix_benchmarking.models as models

from pydantic import BaseModel, constr

class NotebookScaleMetadata(models.Metadata):
    test: enums.TestName
    cluster_info: metadata.ClusterInfo
    settings: metadata.NotebookScaleSettings


class NotebookScaleData(models.ExclusiveModel):
    users: List[user.UserData]
    config: BaseModel
    metrics: Dict[str, models.PrometheusMetric]
    thresholds: BaseModel
    ocp_version: models.SemVer
    rhods_version: models.SemVer


class NotebookScalePayload(models.create_PSAPPayload('rhods-matbench-upload')):
    data: NotebookScaleData
    metadata: NotebookScaleMetadata
