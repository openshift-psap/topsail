import os
import pathlib
import logging
import json, yaml

from projects.core.library import env, config, run, configure_logging, export
import remote_access, podman, prepare_virglrenderer, prepare_llama_cpp


def _run(base_work_dir, cmd, env={}, check=True, capture_stdout=False, machine=True, get_command=False, print_cmd=False):
    podman_cmd = podman.get_podman_command()

    cmd = f"{podman_cmd} {'machine' if machine else ''} {cmd}"
    if get_command:
        return cmd

    return remote_access.run_with_ansible_ssh_conf(
        base_work_dir,
        cmd,
        extra_env=env,
        check=check,
        capture_stdout=capture_stdout,
        print_cmd=print_cmd,
    )

#

def init(base_work_dir):
    name = config.project.get_config("prepare.podman.machine.name", print=False)
    _run(base_work_dir, f"init {name}") # raises an excption if it fails

    return inspect(base_work_dir)

def stop(base_work_dir):
    name = config.project.get_config("prepare.podman.machine.name", print=False)
    return _run(base_work_dir, f"stop {name}")


def start(base_work_dir, use_remoting=None):
    name = config.project.get_config("prepare.podman.machine.name", print=False)

    env = {}

    if use_remoting is None:
        use_remoting = config.project.get_config("prepare.podman.machine.remoting_env.enabled")

    if use_remoting:
        env["DYLD_LIBRARY_PATH"] = prepare_virglrenderer.get_dyld_library_path(base_work_dir) # not working ... (blocked by MacOS when SSHing ...)
        llama_remoting_backend_build_dir = prepare_llama_cpp.get_remoting_build_dir(base_work_dir)
        env["VIRGL_APIR_BACKEND_LIBRARY"] = llama_remoting_backend_build_dir / config.project.get_config("prepare.podman.machine.remoting_env.apir_lib.name")
        env["APIR_LLAMA_CPP_GGML_LIBRARY_PATH"] = llama_remoting_backend_build_dir / config.project.get_config("prepare.podman.machine.remoting_env.ggml_lib.name")
        env |= config.project.get_config("prepare.podman.machine.remoting_env.env")
        prepare_virglrenderer.configure(base_work_dir, use_custom=True)
    else:
        prepare_virglrenderer.configure(base_work_dir, use_custom=False)

    ret = _run(base_work_dir, f"start {name}", env, print_cmd=True)

    if config.project.get_config("prepare.podman.machine.remoting_env.enabled"):

        has_virgl = remote_access.run_with_ansible_ssh_conf(base_work_dir, "lsof -c krunkit | grep virglrenderer", check=False, capture_stdout=True)
        if str(prepare_virglrenderer.get_dyld_library_path(base_work_dir)) not in has_virgl.stdout:
            raise RuntimeError("The custom virglrenderer library is not loaded in krunkit :/")

    return ret


def rm(base_work_dir):
    name = config.project.get_config("prepare.podman.machine.name", print=False)
    return _run(base_work_dir, f"rm {name} --force")

def reset(base_work_dir):
    return _run(base_work_dir, f"reset --force")

#

def set_default_connection(base_work_dir):
    name = config.project.get_config("prepare.podman.machine.name", print=False)
    return _run(base_work_dir, f"system connection default {name}", machine=False)

#


def get_ssh_command_prefix():
    name = config.project.get_config("prepare.podman.machine.name", print=False)
    return _run(None, f"ssh {name}", get_command=True)

#

def is_running(base_work_dir):
    machine_state = inspect(base_work_dir)
    if not machine_state:
        return None

    return machine_state[0]["State"] != "stopped"


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
        if config.project.get_config("prepare.podman.machine.force_configuration"):
            stop(base_work_dir)
            was_stopped = True

    if not was_stopped:
        logging.info("podman machine already running. Skipping the configuration part.")
        return

    configure(base_work_dir)

    start(base_work_dir)

    machine_state = inspect(base_work_dir)
    if not machine_state:
        msg = "Podman machine failed to start :/"
        logging.fatal(msg)
        logging.info(yaml.dump(machine_state))
        raise RuntimeError(msg)

    if config.project.get_config("prepare.podman.machine.set_default"):
        set_default_connection(base_work_dir)
