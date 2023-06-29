from typing import List, Dict

import matrix_benchmarking.models as matbench_models

from pydantic import BaseModel, constr

class QDupPayload(matbench_models.ExclusiveModel):
    qdup: Dict
    lts_payload: List[Dict]
    schema_name: matbench_models.create_schema_field("qdup-payload")

    class Config:   
        fields = {'schema_name': '$schema'}