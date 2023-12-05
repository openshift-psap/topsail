from . import user, metadata, prom

from typing import List, Dict

import matrix_benchmarking.models as matbench_models

from pydantic import BaseModel, constr, Field

class NotebookScaleMetadata(matbench_models.Metadata):
    presets: List[str]
    test: str
    ocp_version: matbench_models.SemVer
    rhods_version: matbench_models.SemVer
    settings: dict


class NotebookScaleData(matbench_models.ExclusiveModel):
    users: List[user.UserData]
    config: BaseModel
    metrics: prom.PromValues
    thresholds: BaseModel
    cluster_info: metadata.ClusterInfo


class NotebookScalePayload(matbench_models.ExclusiveModel):
    schema_name: matbench_models.create_schema_field("rhods-notebooks") = Field(alias="$schema")
    data: NotebookScaleData
    metadata: NotebookScaleMetadata

    class Config:
        fields = {'schema_name': '$schema'}

NotebookScalePayload.update_forward_refs()