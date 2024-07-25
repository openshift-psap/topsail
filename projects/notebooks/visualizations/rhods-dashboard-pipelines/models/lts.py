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


class Payload(matbench_models.ExclusiveModel):
    results: NotebookScaleData
    metadata: NotebookScaleMetadata

    class Config:
        fields = {'schema_name': '$schema'}

Payload.update_forward_refs()
