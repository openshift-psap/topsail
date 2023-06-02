from . import user

from typing import List

import matrix_benchmarking.models as models

from pydantic import BaseModel

class NotebookScaleData(BaseModel):
    users: List[user.UserData]

class NotebookScalePayload(models.PSAPPayload):
    data: NotebookScaleData
