class State:
    def __init__(self):
        self.dependencies = {}
        self.predefined_tasks = {}

        self.resolved = set()

        self.tested = dict()
        self.installed = dict()

        self.dep_file_configuration = {}
        self.cfg_file_configuration = {}
        self.cli_configuration = {}

        self.wdm_mode = None

        self.cli_args = None

        self.dependency_prefixes = {}

state = State()
