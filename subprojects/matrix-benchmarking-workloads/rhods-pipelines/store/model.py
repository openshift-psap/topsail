import enum
import typing

import pydantic

class FromLocalEnvModel(pydantic.BaseModel, extra=pydantic.Extra.forbid):
    pass

class TestConfigModel(pydantic.BaseModel, extra=pydantic.Extra.forbid):
    pass

class ResultModel(pydantic.BaseModel, extra=pydantic.Extra.forbid):
    from_local_env: FromLocalEnvModel
    test_config = TestConfigModel
