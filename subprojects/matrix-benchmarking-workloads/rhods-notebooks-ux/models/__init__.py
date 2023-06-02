from . import user

from typing import List, Dict

import matrix_benchmarking.models as models

from pydantic import BaseModel

class NotebookScaleData(BaseModel):
    users: List[user.UserData]
    config: BaseModel
    metrics: Dict[str, models.PrometheusMetric]
    thresholds: BaseModel
    ocp_version: models.SemVer
    rhods_version: models.SemVer


class NotebookScalePayload(models.PSAPPayload):
    data: NotebookScaleData
