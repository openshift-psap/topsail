from . import enums

from typing import List, Optional

from pydantic import BaseModel

class SubStepData(BaseModel):
    resource_init_time: float
    container_ready_time: float
    user_notification: float

class StepData(BaseModel):
    name: enums.StepName
    status: enums.StepStatus
    duration: float
    substeps: Optional[SubStepData]

class UserData(BaseModel):
    steps: List[StepData]