#! /usr/bin/python3

import yaml
import sys, os
import subprocess
import tempfile
import pathlib
import logging
import selectors

logging.basicConfig(
    level=os.environ.get("LOGLEVEL", "DEBUG"),
    format="%(levelname)6s | %(message)s",
)

try:
    import fire
except ModuleNotFoundError:
    logging.error("WDM requires the Python `fire` package.")
    sys.exit(1)

# ---
import enum
import pydantic
import typing

class TaskType(str, enum.Enum):
    shell = 'shell'
    ansible = 'ansible'

class TaskModel(pydantic.BaseModel):
    name: str
    type: TaskType
    spec: typing.Union[str, list[dict]]

class DependencySpecModel(pydantic.BaseModel):
    requirements: list[str] = None
    tests: list[TaskModel] = None
    install: list[TaskModel] = None

class DependencyModel(pydantic.BaseModel):
    """
    This is the description of a dependency object
    """

    name: str
    spec: DependencySpecModel

# ---

deps = {}
resolved = set()

tested = dict()
installed = dict()

wdm_mode = None
cli_args = None

def subprocess_stdout_to_log(proc, prefix):
    sel = selectors.DefaultSelector()
    sel.register(proc.stdout, selectors.EVENT_READ)
    sel.register(proc.stderr, selectors.EVENT_READ)
    first_stdout = True
    first_stderr = True
    prefix = f" DEBUG | {prefix} |"
    while True:
        for key, _ in sel.select():
            data = key.fileobj.read1().decode()
            if not data:
                if not first_stderr: print("")
                if not first_stdout: print("")
                return

            data = data.replace("\n", "\n"+prefix + " ")

            if key.fileobj is proc.stdout:
                if first_stdout:
                    print(prefix, data, end="")
                    first_stdout = False
                else:
                    print(data, end="")
            else:
                if first_stderr:
                    print(prefix, data, end="")
                    first_stderr = False
                else:
                    print(data, end="")


def run_ansible(task, depth):
    tmp = tempfile.NamedTemporaryFile("w+", dir=os.getcwd(), delete=False)

    play = [
        dict(name=f"Run {task.name}",
             connection="local",
             gather_facts=False,
             hosts="localhost",
             tasks=task.spec,
             )
    ]

    yaml.dump(play, tmp)
    tmp.close()

    env = os.environ.copy()
    dir_path = os.path.dirname(os.path.realpath(__file__))

    env["ANSIBLE_CONFIG"] = cli_args["ansible_config"] if cli_args.get("ansible_config") != None \
        else dir_path + "/../../config/ansible.cfg"

    sys.stdout.flush()
    sys.stderr.flush()

    try:
        proc = subprocess.Popen(["ansible-playbook", tmp.name],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              env=env, stdin=subprocess.PIPE)
        subprocess_stdout_to_log(proc, prefix=task.name)
        proc.wait()
        ret = proc.returncode
    except KeyboardInterrupt:
        logging.error(f"Task '{task}' was interrupted ...")
        sys.exit(1)
    finally:
        os.remove(tmp.name)

    return ret == 0


def run_shell(task, depth):
    cmd = task.spec.strip()

    for line in cmd.split("\n"):
        logging.debug(f">SHELL<| %s", line)

    sys.stdout.flush()
    sys.stderr.flush()
    try:
        proc = subprocess.Popen(["bash", "-ceuo", "pipefail", cmd],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              stdin=subprocess.PIPE)
        subprocess_stdout_to_log(proc, prefix=task.name)
        proc.wait()
        ret = proc.returncode
    except KeyboardInterrupt:
        logging.error(f"Task '{task}' was interrupted ...")
        sys.exit(1)

    return ret == 0

def run(task, depth):
    logging.debug(f"Running '{task.name}' ...")
    type_ = task.type
    if type_ == "shell":
        success = run_shell(task, depth)
    elif type_ == "ansible":
        success = run_ansible(task, depth)
    else:
        logging.error(f"unknown task type: {type_}.")
        sys.exit(1)

    logging.debug(f"Running '{task.name}': %s", "Success" if success else "Failure")
    logging.debug("|___")

    return success


def do_test(dep, depth, print_first_test=True):
    if not dep.spec.tests:
        if dep.spec.install:
            if print_first_test:
                logging.debug(f"Nothing to test for '{dep.name}'. Has install tasks, run them.")
            success = False
        else:
            if print_first_test:
                logging.debug(f"Nothing to test for '{dep.name}'. Doesn't have install tasks, we're good.")
            success = True
        return success

    for task in dep.spec.tests:
        if print_first_test:
            logging.debug(f"Testing '{dep.name}' ...")
            print_first_test = False

        success = run(task, depth) if wdm_mode != "dryrun" else None

        tested[f"{dep.name} -> {task.name}"] = success
        if success:
            return True

    return False


def resolve(dep, depth=0):
    logging.info(f"Treating '{dep.name}' dependency ...")

    if dep.name in resolved:
        logging.info(f"Dependency '{dep.name}' has already need resolved, skipping.")
        return

    for req in dep.spec.requirements or []:
        logging.info(f"Dependency '{dep.name}' needs '{req}' ...")
        try:
            next_dep = deps[req]
        except KeyError as e:
            logging.error(f"missing dependency: {req}")
            sys.exit(1)
        resolve(next_dep, depth=depth+1)

    if do_test(dep, depth) == True:
        if dep.spec.tests:
            logging.debug( f"Dependency '{dep.name}' is satisfied, no need to install.")

    elif wdm_mode in ("dryrun", "test"):
        logging.debug(f"Running in test mode, skipping '{dep.name}' installation.")
        for task in dep.spec.install:
            installed[f"{dep.name} -> {task.name}"] = True
    else:
        first_install = True
        for task in dep.spec.install:
            if first_install:
                first_install = False
                logging.info(f"Installing '{dep.name}' ...")

            if not run(task, depth):
                logging.error(f"install of '{dep.name}' failed.")
                sys.exit(1)

            installed[f"{dep.name} -> {task.name}"] = True

        if first_install:
            # no install task available

            logging.error(f"'{dep.name}' test failed, but no install script provided.")
            sys.exit(1)

        if not do_test(dep, depth, print_first_test=False):
            if dep.spec.tests:
                logging.error(f"'{dep.name}' installed, but test still failing.")
                sys.exit(1)

            logging.info(f"'{dep.name}' installed, but has no test. Continuing nevertheless.")


    resolved.add(dep.name)
    logging.info(f"Done with {dep.name}.")

def wdm_main(kwargs):
    global wdm_mode, cli_args
    wdm_mode = kwargs["wdm_mode"]

    update_env_with_env_files()
    update_kwargs_with_env(kwargs)
    cli_args = kwargs

    wdm_dependency_file = cli_args["dependency_file"]

    if not pathlib.Path(wdm_dependency_file).is_file():
        logging.error(f"Flag 'dependency_file' must point to a valid file. (dependency_file='{wdm_dependency_file}')")
        sys.exit(2)

    # ---

    with open(wdm_dependency_file) as f:
        docs = list(yaml.safe_load_all(f))

    main_target = kwargs["target"]
    for doc in docs:
        if doc is None: continue # empty block
        obj = DependencyModel.parse_obj(doc)
        deps[obj.name] = obj
        if not main_target:
             main_target = obj.name

    resolve(deps[main_target])

    logging.info("All done.")

    if wdm_mode in ("dryrun"):
        logging.info("Would have tested:")
    else:
        logging.info("Tested:")

    has_test_failures = False
    for taskname, success in tested.items():
        logging.info(f"- {'☑ ' if success else ('' if success is None else '❎ ')}{taskname}")
        if success == False: has_test_failures = True

    if installed:
        if wdm_mode in ("test", "dryrun"):
            logging.info("Would have installed:")
        else:
            logging.info("Installed:")
        [logging.info(f"- {taskname}") for taskname in installed]
    else:
        if wdm_mode in ("test", "dryrun"):
            logging.info("Would have installed: nothing.")
        else:
            logging.info("Installed: nothing.")

    if has_test_failures:
        logging.info("Some tests failed, exit with errcode=1.")
        sys.exit(1)


def update_env_with_env_files():
    """
    Overrides the function default args with the flags found in the environment variables files
    """
    for env in ".env", ".env.generated":
        try:
            with open(env) as f:
                for line in f.readlines():
                    key, found , value = line.strip().partition("=")
                    if not found:
                        logging.warning("invalid line in {env}: {line.strip()}")
                        continue
                    if key in os.environ: continue # prefer env to env file
                    os.environ[key] = value
        except FileNotFoundError: pass # ignore missing files


def update_kwargs_with_env(kwargs):
    # override the function default args with the flags found in the environment variables

    for flag, current_value in kwargs.items():
        if current_value: continue # already set, ignore.

        env_value = os.environ.get(f"WDM_{flag.upper()}")
        if not env_value: continue # not set, ignore.
        kwargs[flag] = env_value # override the function arg with the environment variable value


def get_entrypoint(entrypoint_name):

    def entrypoint(dependency_file: str = "./dependencies.yaml",
                   target: str = "",
                   ansible_config: str = None,
                   ):
        """
Run Workload Dependency Manager

Modes:
    dryrun: do not run test nor install tasks.
    test: only test if a dependency is satisfied.
    ensure: test dependencies and install those unsatisfied.

Env:
    WDM_DEPENDENCY_FILE

See the `FLAGS` section for the descriptions.

Return codes:
    2 if an error occured
    1 if the testing is unsuccessful (test mode)
    1 if an installation failed (ensure mode)
    0 if the testing is successful (test mode)
    0 if the dependencies are all satisfied (ensure mode)

Args:
    dependency_file: Path of the dependency file to resolve.
    target: Dependency to resolve. If empty, take the first entry defined the dependency file.
    ansible_config: Ansible config file (for Ansible tasks).
"""

        kwargs = dict(locals()) # capture the function arguments
        kwargs["wdm_mode"] = entrypoint_name

        return wdm_main(kwargs)

    return entrypoint

def show_example():
    print("""
Examples:
    $ export WDM_DEPENDENCY_FILE=...
    $ wdm test has_nfd
    $ wdm ensure has_gpu_operator
---
name: has_gpu_operator
spec:
  requirements:
  - has_nfd
  tests:
  - name: has_nfd_operatorhub
    type: shell
    spec: oc get pod -l app.kubernetes.io/component=gpu-operator -A -oname
  install:
  - name: install_gpu_operator
    type: shell
    spec: ./run_toolbox.py gpu_operator deploy_from_operatorhub
  - name: install_gpu_operator
    type: shell
    spec: ./run_toolbox.py gpu_operator wait_deployment
---
name: has_nfd
spec:
  tests:
  - name: has_nfd_labels
    type: shell
    spec: ./run_toolbox.py nfd has_labels
  install:
  - name: install_nfd_from_operatorhub
    type: shell
    spec: ./run_toolbox.py nfd_operator deploy_from_operatorhub
""")

class WDM_Entrypoint:
    def __init__(self):
        self.dryrun = get_entrypoint("dryrun")
        self.ensure = get_entrypoint("ensure")
        self.test = get_entrypoint("test")
        self.example = show_example

def main():
    # Print help rather than opening a pager
    fire.core.Display = lambda lines, out: print(*lines, file=out)

    # Launch CLI, get a runnable
    runnable = None
    runnable = fire.Fire(WDM_Entrypoint())

    # Run the actual workload
    if hasattr(runnable, "_run"):
        runnable._run()
    else:
        # CLI didn't resolve completely - either by lack of arguments
        # or use of `--help`. This is okay.
        pass

if __name__ == "__main__":
    main()
