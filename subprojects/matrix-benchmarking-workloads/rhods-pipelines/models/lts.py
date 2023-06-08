import matrix_benchmarking.models as matbench_models

from typing import Any, Dict, List, Optional, Union

from .. import models as pipelines_models

class PipelinesScaleTestMetadata(matbench_models.Metadata):
    presets: List[str]

    ocp_version: matbench_models.SemVer
    rhods_version: matbench_models.SemVer
    user_count: int
    config: Any

class PipelinesScaleTestResults(matbench_models.ExclusiveModel):
    # nothing for now
    ...

class PipelinesScaleTestPayload(matbench_models.ExclusiveModel):
    metadata: PipelinesScaleTestMetadata
    results: PipelinesScaleTestResults
