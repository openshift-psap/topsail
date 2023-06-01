import matrix_benchmarking.models as models

from pydantic import BaseModel

class NotebookScaleData(BaseModel):
    pass

class NotebookScalePayload(models.PSAPPayload):
    data: NotebookScaleData
