import logging
import pathlib
import sys

import wdm
import wdm.model as model
import wdm.env_config as env_config
import wdm.populate as populate
import wdm.resolve as resolve

def print_summary():
    logging.info("All done.\n")

    if wdm.state.wdm_mode in ("dryrun"):
        logging.info("Would have tested:")
    else:
        logging.info("Tested:")

    for taskname, success in wdm.state.tested.items():
        logging.info(f"- {'☑ ' if success else ('' if success is None else '❎ ')}{taskname}")

    if wdm.state.installed:
        if wdm.state.wdm_mode in ("test", "dryrun"):
            logging.info("Would have installed:")
        else:
            logging.info("Installed:")
        [logging.info(f"- {taskname}") for taskname in wdm.state.installed]
    else:
        if wdm.state.wdm_mode in ("test", "dryrun"):
            logging.info("Would have installed: nothing.")
        else:
            logging.info("Installed: nothing.")


def has_failures():
    has_test_failures = False
    for taskname, success in wdm.state.tested.items():
        if success == False: return True

    return False


def wdm_main(wdm_mode, cli_args):
    wdm.state.wdm_mode = wdm_mode
    wdm.state.cli_args = cli_args

    cli_config = wdm.state.cli_args["config"]
    if cli_config:
        wdm.state.cli_configuration = env_config.get_config_from_cli(cli_config)

    subproject_dirname = pathlib.Path(__file__).resolve().parent.parent
    for filename in (subproject_dirname / "predefined.d").glob("*"):
        populate.populate_predefined_tasks(filename, wdm.state.predefined_tasks)

    for filename in (subproject_dirname / "library.d").glob("*"):
        _name, _, ext = filename.name.rpartition(".")

        name = _name if ext in ("yaml", "yml") else filename.name
        prefix = f"library.{name}."
        populate.populate_dependencies(filename, wdm.state.dependencies, wdm.state.dependency_prefixes, prefix=prefix)

    if wdm.state.cli_args["library"]:
        if not wdm.state.cli_args.get("target") and wdm.state.wdm_mode != "list":
            logging.error("Flag 'target' cannot be empty when 'dependency-file' is set to 'library'")
            sys.exit(1)

    config_file = wdm.state.cli_args["config_file"]
    if not config_file:
        config_file = pathlib.Path(".wdm_config")
        if not config_file.is_file():
            config_file = "no"


    if config_file != "no":
        config_file = pathlib.Path(config_file)
        if not config_file.is_file():
            logging.error(f"Flag 'config_file' must point to a valid dependency file (config_file={config_file})")
            sys.exit(1)
        wdm.state.cfg_file_configuration = env_config.get_config_from_kv_file(config_file)

    file_first_target = None

    wdm_dependency_file = wdm.state.cli_args["dependency_file"]
    if pathlib.Path(wdm_dependency_file).is_file():
        file_first_target = populate.populate_dependencies(wdm_dependency_file,
                                                           wdm.state.dependencies,
                                                           wdm.state.dependency_prefixes,
                                                           prefix="",
                                                           file_configuration=wdm.state.dep_file_configuration)
    elif not wdm.state.cli_args["library"]:
        logging.error(f"Flag 'dependency_file' must point to a valid file (dependency_file='{wdm_dependency_file}'), or enable the 'library' flag to pickup the main target from the library files only.")
        sys.exit(2)

    if wdm.state.wdm_mode == "list":
        for target in wdm.state.dependencies:
            print(f"- {target}")
        sys.exit(0)

    target = wdm.state.cli_args.get("target") or file_first_target
    dependency = wdm.state.dependencies.get(target)
    if not dependency:
        logging.error(f"Main dependency '{target}' does not exist.")
        sys.exit(1)

    resolve.resolve(dependency)

    print_summary()

    if has_failures():
        logging.warning("Test failed, exit with errcode=1.")
        sys.exit(1)
