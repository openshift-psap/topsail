from . import enums

import matrix_benchmarking.models as matbench_models

from typing import List, Optional


class SubStepData(matbench_models.ExclusiveModel):
    resource_init_time: float
    container_ready_time: float
    user_notification: float

class StepData(matbench_models.ExclusiveModel):
    name: enums.StepName
    status: enums.StepStatus
    duration: float
    substeps: Optional[SubStepData]

class UserData(matbench_models.ExclusiveModel):
    steps: List[StepData]
    succeeded: bool
    hostname: str
