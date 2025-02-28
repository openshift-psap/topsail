import os
import pathlib
import logging
import json, yaml

from projects.core.library import env, config, run, configure_logging, export
import remote_access, podman


def _run(base_work_dir, cmd, check=True, capture_stdout=False, machine=True):
    podman_bin = podman.get_podman_binary()

    return remote_access.run_with_ansible_ssh_conf(
        base_work_dir,
        f"{podman_bin} {'machine' if machine else ''} {cmd}",
        check=check,
        capture_stdout=capture_stdout,
    )

#

def init(base_work_dir):
    name = config.project.get_config("prepare.podman.machine.name", print=False)
    _run(base_work_dir, f"init {name}") # raises an excption if it fails

    return inspect(base_work_dir)

def delete(base_work_dir):
    name = config.project.get_config("prepare.podman.machine.name", print=False)
    return _run(base_work_dir, f"rm {name}")


def stop(base_work_dir):
    name = config.project.get_config("prepare.podman.machine.name", print=False)
    return _run(base_work_dir, f"stop {name}")


def start(base_work_dir):
    name = config.project.get_config("prepare.podman.machine.name", print=False)
    return _run(base_work_dir, f"start {name}")

#

def set_default_connection(base_work_dir):
    name = config.project.get_config("prepare.podman.machine.name", print=False)
    return _run(base_work_dir, f"system connection default {name}", machine=False)

#

def info(base_work_dir):
    return _run(base_work_dir, "info")


def inspect(base_work_dir):
    name = config.project.get_config("prepare.podman.machine.name", print=False)
    inspect_cmd = _run(base_work_dir, f"inspect {name}", capture_stdout=True, check=False)
    if inspect_cmd.returncode != 0:
        if "VM does not exist" in inspect_cmd.stdout:
            logging.info("podman_machine: inspect: VM does not exist")
        else:
            logging.error(f"podman_machine: inspect: unhandled status: {inspect_cmd.stdout.strip()}")
        return None


    return json.loads(inspect_cmd.stdout)


def configure(base_work_dir):
    name = config.project.get_config("prepare.podman.machine.name", print=False)
    configuration = config.project.get_config("prepare.podman.machine.configuration")
    config_str = " ".join(f"--{k}={v}" for k, v in configuration.items())

    return _run(base_work_dir, f"set {config_str} {name}")

#

def configure_and_start(base_work_dir, force_restart=True):
    machine_state = inspect(base_work_dir)
    if not machine_state:
        machine_state = init(base_work_dir)
    was_stopped = machine_state[0]["State"] == "stopped"

    if force_restart and not was_stopped:
        stop(base_work_dir)
        was_stopped = True

    if was_stopped:
        configure(base_work_dir)

        start(base_work_dir)
    else:
        logging.info("podman machine already running. Skipping the configuration part.")

    machine_state = inspect(base_work_dir)
    if not machine_state:
        msg = "Podman machine failed to start :/"
        logging.fatal(msg)
        logging.info(yaml.dump(machine_state))
        raise RuntimeError(msg)

    if config.project.get_config("prepare.podman.machine.set_default"):
        set_default_connection(base_work_dir)
