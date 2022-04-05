import selectors
import tempfile
import subprocess
import os, sys
import logging
import yaml
import pathlib

import wdm
import wdm.env_config as env_config
import wdm.model as model

def run(dep, task, *, is_test):
    logging.debug(f"Running %s task '{task.name}' ...", "test" if is_test else "install")

    try:
        fn = TaskTypeFunctions[task.type]
    except KeyError:
        logging.error(f"Unknown task type: {task.type}.")
        sys.exit(1)

    success = fn(dep, task, is_test=is_test)

    if success != None:
        logging.info("%s of '%s': %s", "Testing" if is_test else "Installation", task.name, "Success" if success else "Failed")

    return success


def subprocess_stdout_to_log(proc, prefix):
    sel = selectors.DefaultSelector()
    sel.register(proc.stdout, selectors.EVENT_READ)
    sel.register(proc.stderr, selectors.EVENT_READ)

    prefix = f"{prefix} |"
    pending = dict(stdout="", stderr="")
    while True:
        for key, _ in sel.select():
            read = key.fileobj.read1

            # remove when Py 3.6 is not supported anymore:
            if sys.version_info.minor <= 6:
                read = key.fileobj.read

            data = read().decode()
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

    repo_ansible_config = pathlib.Path(__file__).parent.parent.parent.parent / "config" / "ansible.cfg"
    cli_ansible_config = wdm.state.cli_args.get("ansible_config")
    ENV_ANSIBLE_CONFIG = "ANSIBLE_CONFIG"

    env = os.environ.copy()

    if cli_ansible_config:
        env[ENV_ANSIBLE_CONFIG] = cli_ansible_config

    elif ENV_ANSIBLE_CONFIG not in env:
        env[ENV_ANSIBLE_CONFIG] = repo_ansible_config

    sys.stdout.flush()
    sys.stderr.flush()

    tmp = tempfile.NamedTemporaryFile("w+", dir=os.getcwd(), delete=False)
    yaml.dump(play, tmp)
    tmp.close()

    cmd = ["ansible-playbook", tmp.name]

    for key, value in env_config.get_task_configuration_kv(dep, task).items():
        logging.debug(f"[ansible] extra var: %s=%s", key, value)
        cmd += ["--extra-vars", f"{key}={value}"]

    logging.debug("[ansible] command: %s", " ".join(cmd))

    if wdm.state.wdm_mode == "dryrun":
        logging.info("Dry mode, skipping execution.")
        return None

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

def run_shell(dep, task, *, is_test):
    logging.debug(f"[shell] Running '{task.name}' ...")

    cmd = task.spec.strip()

    env = os.environ.copy()

    for key, value in env_config.get_task_configuration_kv(dep, task).items():
        env[key] = value
        logging.debug(f"[shell] env %s=%s", key, value)

    for line in cmd.split("\n"):
        logging.debug(f"[shell] %s", line)

    sys.stdout.flush()
    sys.stderr.flush()

    popen_cmd = ["bash", "-cxeuo", "pipefail", cmd]

    if wdm.state.wdm_mode == "dryrun":
        logging.info("Dry mode, skipping execution.")
        return None

    try:
        proc = subprocess.Popen(popen_cmd,
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
    try:
        predefined_task = wdm.state.predefined_tasks[task.spec.name].copy()
    except KeyError:
        logging.error(f"{_dep.name}/{task.name}: Could not find predefined task {task.spec.name}")
        logging.info("Available predefined tasks: %s", ", ".join(wdm.state.predefined_tasks))
        sys.exit(1)

    predefined_task.name = f"{task.name} | predefined({task.spec.name})"

    logging.debug(f"[predefined] Running '{predefined_task.name}' ...")
    dep = _dep.copy()

    if not dep.config_values:
        dep.config_values = {}
    dep.config_values.update(task.spec.args)

    return run(dep, predefined_task, is_test=is_test)

def run_toolbox(dep, task, *, is_test):
    try:
        predefined_toolbox_task = wdm.state.predefined_tasks["run_toolbox"]
    except KeyError:
        logging.error("Could not find the task 'run_toolbox' in the predefined tasks. "
                      "That's unexpected ...")
        logging.info("Available predefined tasks: %s", ", ".join(wdm.state.predefined_tasks.keys()))
        sys.exit(1)

    task_config = env_config.get_task_configuration_kv(dep, task)
    def apply_config(val):
        for key, value in task_config.items():
            val = val.replace(f"${key}", value)
            val = val.replace(f"${{{key}}}", value)

        return val

    obj = dict(
        name=f"{task.name} | toolbox()",
        configuration=task.configuration,
        spec=dict(
            name=predefined_toolbox_task.name,
            args=dict(
                group=apply_config(task.spec.group),
                command=apply_config(task.spec.command),
                args=apply_config(" ".join(task.spec.args or []))
            )
        )
    )
    toolbox_task = model.PredefinedTaskModel.parse_obj(obj)

    logging.debug(f"[toolbox] Running '{toolbox_task.name}' ...")
    return run_predefined(dep, toolbox_task, is_test=is_test)

TaskTypeFunctions = {
    model.TaskType.shell: run_shell,
    model.TaskType.ansible: run_ansible,
    model.TaskType.predefined: run_predefined,
    model.TaskType.toolbox: run_toolbox,
}
