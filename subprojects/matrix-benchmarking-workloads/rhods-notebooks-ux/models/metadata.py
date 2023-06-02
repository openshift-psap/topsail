from . import user

from typing import List, Dict

import matrix_benchmarking.models as models

from pydantic import BaseModel, constr


class NotebookScaleSettings(BaseModel):
    repeat: str
    test_case: str
    user_count: int
    exclude_tags: str