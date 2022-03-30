import enum
import typing

import pydantic


class TaskType(str, enum.Enum):
    shell = 'shell'
    ansible = 'ansible'
    toolbox = 'toolbox'
    predefined = 'predefined'

class TaskAbstractModel(pydantic.BaseModel):
    name: str
    type: TaskType
    configuration: list[str] = None

# ---

class ToolboxTaskSpecModel(pydantic.BaseModel, extra=pydantic.Extra.forbid):
    group: str
    command: str
    args: list[str] = None

class ToolboxTaskModel(TaskAbstractModel, extra=pydantic.Extra.forbid):
    type: str = pydantic.Field(TaskType.toolbox.value, const=True)
    spec: ToolboxTaskSpecModel

# ---

class ShellTaskModel(TaskAbstractModel, extra=pydantic.Extra.forbid):
    type: str = pydantic.Field(TaskType.shell.value, const=True)
    spec: str

# ---

class AnsibleTaskModel(TaskAbstractModel, extra=pydantic.Extra.forbid):
    type: str = pydantic.Field(TaskType.ansible.value, const=True)
    spec: list[dict]

# ---

class PredefinedSpecTaskModel(pydantic.BaseModel, extra=pydantic.Extra.forbid):
    name: str
    args: dict[str, str]

class PredefinedTaskModel(TaskAbstractModel, extra=pydantic.Extra.forbid):
    type: str = pydantic.Field(TaskType.predefined.value, const=True)
    spec: PredefinedSpecTaskModel

# ---

TaskModels = typing.Union[ShellTaskModel, AnsibleTaskModel, PredefinedTaskModel, ToolboxTaskModel]

class DependencySpecModel(pydantic.BaseModel, extra=pydantic.Extra.forbid):
    requirements: list[str] = None
    configuration: list[str] = None
    test: list[TaskModels] = None
    install: list[TaskModels] = None

class DependencyModel(pydantic.BaseModel, extra=pydantic.Extra.forbid):
    """
    This is the description of a dependency object
    """

    name: str
    config_values: dict[str, str] = None
    spec: DependencySpecModel = None
