import logging
import pathlib
import sys

import wdm.model as model
import wdm.env_config as env_config
import wdm.populate as populate
import wdm.resolve as resolve

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


def print_summary():
    logging.info("All done.\n")

    if state.wdm_mode in ("dryrun"):
        logging.info("Would have tested:")
    else:
        logging.info("Tested:")

    for taskname, success in state.tested.items():
        logging.info(f"- {'☑ ' if success else ('' if success is None else '❎ ')}{taskname}")

    if state.installed:
        if state.wdm_mode in ("test", "dryrun"):
            logging.info("Would have installed:")
        else:
            logging.info("Installed:")
        [logging.info(f"- {taskname}") for taskname in state.installed]
    else:
        if state.wdm_mode in ("test", "dryrun"):
            logging.info("Would have installed: nothing.")
        else:
            logging.info("Installed: nothing.")


def has_failures():
    has_test_failures = False
    for taskname, success in state.tested.items():
        if success == False: return True

    return False


def wdm_main(wdm_mode, cli_args):
    state.wdm_mode = wdm_mode
    state.cli_args = cli_args

    cli_config = state.cli_args["config"]
    if cli_config:
        state.cli_configuration = env_config.get_config_from_cli(cli_config)

    subproject_dirname = pathlib.Path(__file__).resolve().parent.parent
    for filename in (subproject_dirname / "predefined.d").glob("*"):
        populate.populate_predefined_tasks(filename, state.predefined_tasks)

    for filename in (subproject_dirname / "library.d").glob("*"):
        _name, _, ext = filename.name.rpartition(".")

        name = _name if ext in ("yaml", "yml") else filename.name
        prefix = f"library.{name}."
        populate.populate_dependencies(filename, state.dependencies, state.dependency_prefixes, prefix=prefix)

    if state.cli_args["library"]:
        if not state.cli_args.get("target") and state.wdm_mode != "list":
            logging.error("Flag 'target' cannot be empty when 'dependency-file' is set to 'library'")
            sys.exit(1)

    config_file = state.cli_args["config_file"]
    if not config_file:
        config_file = pathlib.Path(".wdm_config")
        if not config_file.is_file():
            config_file = "no"


    if config_file != "no":
        config_file = pathlib.Path(config_file)
        if not config_file.is_file():
            logging.error(f"Flag 'config_file' must point to a valid dependency file (config_file={config_file})")
            sys.exit(1)
        state.cfg_file_configuration = env_config.get_config_from_kv_file(config_file)

    file_first_target = None

    wdm_dependency_file = state.cli_args["dependency_file"]
    if pathlib.Path(wdm_dependency_file).is_file():
        file_first_target = populate.populate_dependencies(wdm_dependency_file,
                                                           state.dependencies,
                                                           state.dependency_prefixes,
                                                           prefix="",
                                                           file_configuration=state.dep_file_configuration)
    elif not state.cli_args["library"]:
        logging.error(f"Flag 'dependency_file' must point to a valid file (dependency_file='{wdm_dependency_file}'), or enable the 'library' flag to pickup the main target from the library files only.")
        sys.exit(2)

    if state.wdm_mode == "list":
        for target in state.dependencies:
            print(f"- {target}")
        sys.exit(0)

    target = state.cli_args.get("target") or file_first_target
    dependency = state.dependencies.get(target)
    if not dependency:
        logging.error(f"Main dependency '{target}' does not exist.")
        sys.exit(1)

    resolve.resolve(dependency)

    print_summary()

    if has_failures():
        logging.warning("Test failed, exit with errcode=1.")
        sys.exit(1)
