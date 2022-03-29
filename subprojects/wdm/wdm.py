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

file_configuration = {}

# ---

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

class ToolboxTaskSpecModel(pydantic.BaseModel):
    group: str
    command: str
    args: list[str] = None

class ToolboxTaskModel(TaskAbstractModel):
    type: str = pydantic.Field(TaskType.toolbox.value, const=True)
    spec: ToolboxTaskSpecModel

# ---

class ShellTaskModel(TaskAbstractModel):
    type: str = pydantic.Field(TaskType.shell.value, const=True)
    spec: str

# ---

class AnsibleTaskModel(TaskAbstractModel):
    type: str = pydantic.Field(TaskType.ansible.value, const=True)
    spec: list[dict]

# ---

class PredefinedSpecTaskModel(pydantic.BaseModel):
    name: str
    args: dict[str, str]

class PredefinedTaskModel(TaskAbstractModel):
    type: str = pydantic.Field(TaskType.predefined.value, const=True)
    spec: PredefinedSpecTaskModel

# ---

TaskModels = typing.Union[ShellTaskModel, AnsibleTaskModel, PredefinedTaskModel, ToolboxTaskModel]

class DependencySpecModel(pydantic.BaseModel):
    requirements: list[str] = None
    configuration: list[str] = None
    test: list[TaskModels] = None
    install: list[TaskModels] = None

class DependencyModel(pydantic.BaseModel):
    """
    This is the description of a dependency object
    """

    name: str
    configuration: dict = None
    spec: DependencySpecModel = None

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

    prefix = f"{prefix} |"
    pending = dict(stdout="", stderr="")
    while True:
        for key, _ in sel.select():
            data = key.fileobj.read1().decode()
            if not data:
                for out in pending.keys():
                    if pending[out]:
                        logging.debug("%s %s", prefix, pending[out])
                return

            is_stdout = key.fileobj is proc.stdout
            is_std = dict(stdout=is_stdout, stderr=not is_stdout)

            for line in data.split("\n")[:-1]:
                for out in pending.keys():
                    if is_std[out] and pending[out]:
                        line = f"{pending[out]}{line}"
                        pending[out] = ""

                logging.debug("%s %s", prefix, line)

            unfinished_line = data.rpartition("\n")[-1]
            for out in pending.keys():
                if is_std[out] and unfinished_line:
                    pending[out] = unfinished_line


def run_ansible(dep, task, *, is_test):
    play = [
        dict(name=f"Run {task.name}",
             connection="local",
             gather_facts=False,
             hosts="localhost",
             tasks=task.spec,
             )
    ]

    env = os.environ.copy()
    dir_path = os.path.dirname(os.path.realpath(__file__))

    env["ANSIBLE_CONFIG"] = cli_args["ansible_config"] if cli_args.get("ansible_config") != None \
        else dir_path + "/../../config/ansible.cfg"

    sys.stdout.flush()
    sys.stderr.flush()

    tmp = tempfile.NamedTemporaryFile("w+", dir=os.getcwd(), delete=False)
    yaml.dump(play, tmp)
    tmp.close()

    cmd = ["ansible-playbook", tmp.name]

    for key, value in get_configuration_kv(dep, task).items():
        logging.debug(f"[ansible] define %s=%s", key, value)
        cmd += ["-e", f"{key}={value}"]

    logging.debug("[ansible] %s", " ".join(cmd))
    try:
        proc = subprocess.Popen(cmd,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              env=env, stdin=subprocess.PIPE)
        subprocess_stdout_to_log(proc, prefix=task.name)
        proc.wait()
        ret = proc.returncode
    except KeyboardInterrupt:
        print()
        logging.error(f"Task '{task.name}' was interrupted ...")
        sys.exit(1)
    finally:
        os.remove(tmp.name)

    return ret == 0


def get_configuration_kv(dep, task):
    kv = {}
    for key in ([] + (dep.spec.configuration or []) + (task.configuration or [])):
        value = None
        try: value = dep.configuration[key]
        except (KeyError, TypeError): pass

        if value is None:
            try: value = file_configuration[key]
            except KeyError: pass

        if value is None:
            logging.error(f"Could not find a value for the configuration key '%s'", key)
            sys.exit(1)

        kv[key] = value

    return kv

def run_shell(dep, task, *, is_test):
    logging.debug(f"[shell] Running '{task.name}' ...")
    if not isinstance(task.spec, str): import pdb;pdb.set_trace()
    cmd = task.spec.strip()

    env = os.environ.copy()

    for key, value in get_configuration_kv(dep, task).items():
        env[key] = value
        logging.debug(f"[shell] env %s=%s", key, value)

    for line in cmd.split("\n"):
        logging.debug(f"[shell] %s", line)

    sys.stdout.flush()
    sys.stderr.flush()
    try:
        proc = subprocess.Popen(["bash", "-ceuo", "pipefail", cmd],
                                env=env,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                stdin=subprocess.PIPE)

        subprocess_stdout_to_log(proc, prefix=task.name)
        proc.wait()
        ret = proc.returncode
    except KeyboardInterrupt:
        logging.error(f"Task '{task}' was interrupted ...")
        sys.exit(1)

    return ret == 0

def run_predefined(_dep, task, *, is_test):
    predefined_task = predefined_tasks[task.spec.name].copy()

    predefined_task.name = f"{task.name} | predefined({task.spec.name})"

    logging.debug(f"[predefined] Running '{predefined_task.name}' ...")
    dep = _dep.copy()

    if not dep.configuration:
        dep.configuration = {}
    dep.configuration.update(task.spec.args)
    run(dep, predefined_task, is_test=is_test)

def run_toolbox(dep, task, *, is_test):
    toolbox_task = predefined_tasks["run_toolbox"]
    predefined_toolbox_task = PredefinedTaskModel.parse_obj(
        dict(
            name=f"{task.name} | toolbox()",
            spec=dict(
                name=toolbox_task.name,
                args=dict(
                    group=task.spec.group,
                    command=task.spec.command,
                    args=task.spec.args or "",
                )
            )
        )
    )
    logging.debug(f"[toolbox] Running '{predefined_toolbox_task.name}' ...")
    run_predefined(dep, predefined_toolbox_task, is_test=is_test)

TaskTypeFunctions = {
    TaskType.shell: run_shell,
    TaskType.ansible: run_ansible,
    TaskType.predefined: run_predefined,
    TaskType.toolbox: run_toolbox,
}

def run(dep, task, *, is_test):
    logging.debug(f"Running %s task '{task.name}' ...", "test" if is_test else "install")

    try:
        fn = TaskTypeFunctions[task.type]
    except KeyError:
        logging.error(f"unknown task type: {task.type}.")
        sys.exit(1)

    success = fn(dep, task, is_test=is_test)

    logging.info("%s of '%s': %s", "Testing" if is_test else "Installation", task.name, "Success" if success else "Failed")

    return success


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

        success = run(dep, task, is_test=True) if wdm_mode != "dryrun" else None

        tested[f"{dep.name} -> {task.name}"] = success
        if success:
            return True

    return False

def resolve_task_requirement(requirement):
    try:
        next_dep = deps[requirement]
    except KeyError as e:
        logging.error(f"missing required dependency: {req}")
        sys.exit(1)

    return resolve(next_dep)

def resolve_task_config_requirement(config_requirements):
    for config_key in config_requirements:
        if config_key in file_configuration: continue

        logging.error(f"missing required configuration dependency: {config_key}")
        logging.info(f"Available configuration keys: {', '.join(file_configuration.keys())}")
        sys.exit(1)

def resolve(dep):
    logging.info(f"Treating '{dep.name}' dependency ...")

    if dep.name in resolved:
        logging.info(f"Dependency '{dep.name}' has already need resolved, skipping.")
        return

    if dep.spec.configuration:
        resolve_task_config_requirement(dep.spec.configuration)

    for req in dep.spec.requirements or []:
        logging.info(f"Dependency '{dep.name}' needs '{req}' ...")
        resolve_task_requirement(req)

    if do_test(dep) == True:
        if dep.spec.test:
            logging.debug( f"Dependency '{dep.name}' is satisfied, no need to install.")

    elif wdm_mode in ("dryrun", "test"):
        logging.debug(f"Running in test mode, skipping '{dep.name}' installation.")
        for task in dep.spec.install:
            installed[f"{dep.name} -> {task.name}"] = True
    else:
        first_install = True
        for task in dep.spec.install or []:
            if first_install:
                first_install = False
                logging.info(f"Installing '{dep.name}' ...")

            if not run(dep, task, is_test=False):
                logging.error(f"Installation of '{dep.name}' failed.")
                sys.exit(1)

            installed[f"{dep.name} -> {task.name}"] = True

        if first_install:
            # no install task available

            logging.error(f"'{dep.name}' test failed, but no install script provided.")
            sys.exit(1)

        if not do_test(dep, print_first_test=False):
            if dep.spec.test:
                logging.error(f"'{dep.name}' installed, but test still failing.")
                sys.exit(1)

            logging.info(f"'{dep.name}' installed, but has no test. Continuing nevertheless.")


    resolved.add(dep.name)
    logging.info(f"Done with '{dep.name}'.\n")

predefined_tasks = dict()

def populate_predefined_tasks():
    global predefined_tasks

    subproject_dirname = pathlib.Path(__file__).resolve().parent
    with open(subproject_dirname / "predefined.yaml") as f:
        docs = list(yaml.safe_load_all(f))

    class Model(pydantic.BaseModel):
        task: TaskModels

    for doc in docs:
        if doc is None: continue # empty block
        try:
            obj = Model.parse_obj(dict(task=doc))
            task = obj.task
        except pydantic.error_wrappers.ValidationError as e:
            logging.error(f"Failed to parse the YAML predefined file: {e}")
            logging.info("Faulty YAML entry:\n" + yaml.dump(doc))
            sys.exit(1)
        if task.name in predefined_tasks:
            logging.warning(f"Predefined task '{obj.name}' already known. Keeping only the first one.")
            continue

        predefined_tasks[task.name] = task

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

    populate_predefined_tasks()

    with open(wdm_dependency_file) as f:
        docs = list(yaml.safe_load_all(f))

    main_target = kwargs["target"]
    for doc in docs:
        if doc is None: continue # empty block

        try: obj = DependencyModel.parse_obj(doc)
        except pydantic.error_wrappers.ValidationError as e:
            logging.error(f"Failed to parse the YAML dependency file: {e}")
            logging.info("Faulty YAML entry:\n" + yaml.dump(doc))
            sys.exit(1)


        if not obj.spec:
            if file_configuration:
                logging.error("File configuration already populated ... (%s)", file_configuration["__name__"])
                sys.exit(1)

            file_configuration.update(obj.configuration)
            file_configuration["__name__"] = obj.name
            continue

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
        logging.info("Test failed, exit with errcode=1.")
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
  test:
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
  test:
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
