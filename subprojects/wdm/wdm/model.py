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
    configuration: typing.List[str] = None

# ---

class ToolboxTaskSpecModel(pydantic.BaseModel, extra=pydantic.Extra.forbid):
    group: str
    command: str
    args: typing.List[str] = None

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
    spec: typing.List[dict]

# ---

class PredefinedSpecTaskModel(pydantic.BaseModel, extra=pydantic.Extra.forbid):
    name: str
    args: typing.Dict[str, str]

class PredefinedTaskModel(TaskAbstractModel, extra=pydantic.Extra.forbid):
    type: str = pydantic.Field(TaskType.predefined.value, const=True)
    spec: PredefinedSpecTaskModel

# ---

TaskModels = typing.Union[ShellTaskModel, AnsibleTaskModel, PredefinedTaskModel, ToolboxTaskModel]

class DependencySpecModel(pydantic.BaseModel, extra=pydantic.Extra.forbid):
    requirements: typing.List[str] = None
    configuration: typing.List[str] = None
    test: typing.List[TaskModels] = None
    install: typing.List[TaskModels] = None

class DependencyModel(pydantic.BaseModel, extra=pydantic.Extra.forbid):
    """
    This is the description of a dependency object
    """

    name: str
    config_values: typing.Dict[str, str] = None
    spec: DependencySpecModel = None
