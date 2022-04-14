import logging
import sys

import wdm

import wdm.model as model
import wdm.env_config as env_config
import wdm.run as run

def do_test(dep, print_first_test=True):
    if not dep.spec.test:
        if dep.spec.install:
            if print_first_test:
                logging.debug(f"Nothing to test for '{dep.name}'. Has install tasks, run them.")
            success = False
        else:
            if print_first_test:
                logging.debug(f"Nothing to test for '{dep.name}'. Doesn't have install tasks, we're good.")
            success = True
        return success

    for task in dep.spec.test:
        if print_first_test:
            logging.debug(f"Testing '{dep.name}' ...")
            print_first_test = False

        success = run.run(dep, task, is_test=True)

        wdm.state.tested[f"{dep.name} -> {task.name}"] = success
        if success:
            return True

    return success # False or None


def resolve_task_requirement(dep, requirement_name):
    prefix = wdm.state.dependency_prefixes[dep.name]

    next_dep = None
    for name in f"{prefix}{requirement_name}", requirement_name:
        try: next_dep = wdm.state.dependencies[name]
        except KeyError: pass

    if next_dep is None:
        pfix = f"[{prefix}]" if prefix else ""
        logging.error(f"Missing required dependency: {pfix}{requirement_name}")
        sys.exit(1)

    return resolve(next_dep)


def resolve_task_config_requirement(dep, config_requirements):
    kv = env_config.get_configuration_kv(dep)

    missing = [config_key for config_key in config_requirements if config_key not in kv]
    for config_key in missing:
        logging.error(f"Missing required configuration dependency: {config_key}")

    if missing:
        logging.info(f"Available configuration keys: {', '.join(kv.keys())}")
        sys.exit(1)

def resolve(dep):
    logging.info(f"Resolving '{dep.name}' dependency ...")

    if dep.name in wdm.state.resolved:
        logging.info(f"Dependency '{dep.name}' has already need resolved, skipping.")
        return

    if dep.spec.configuration:
        resolve_task_config_requirement(dep, dep.spec.configuration)

    for req in dep.spec.requirements or []:
        logging.info(f"Dependency '{dep.name}' needs '{req}' ...")
        resolve_task_requirement(dep, req)

    if do_test(dep) == True:
        if dep.spec.test:
            logging.debug( f"Dependency '{dep.name}' is satisfied, no need to install.")

    elif wdm.state.wdm_mode == "test":

        for task in dep.spec.install:
            logging.debug(f"Running in {'test' if wdm.state.wdm_mode == 'test' else 'dry'} mode, "
                          f"skipping {task.name} installation.")
            wdm.state.installed[f"{dep.name} -> {task.name}"] = True
    else:
        first_install = True
        for task in dep.spec.install or []:
            if first_install:
                first_install = False
                logging.info(f"Installing '{dep.name}' ...")

            if run.run(dep, task, is_test=False) == False:
                logging.error(f"Installation of '{dep.name}' failed.")
                sys.exit(1)

            wdm.state.installed[f"{dep.name} -> {task.name}"] = True

        if first_install and wdm.state.wdm_mode != "dryrun":
            # no install task available
            logging.error(f"'{dep.name}' test failed, but no install script provided.")
            sys.exit(1)

        if do_test(dep, print_first_test=False) == False:
            if dep.spec.test:
                logging.error(f"'{dep.name}' installed, but test still failing.")
                sys.exit(1)

            logging.info(f"'{dep.name}' installed, but has no test. Continuing nevertheless.")


    wdm.state.resolved.add(dep.name)
    logging.info(f"Done with '{dep.name}'.\n")
