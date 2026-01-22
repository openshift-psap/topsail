import os
import pathlib
import logging
import json, yaml

from projects.core.library import config, run, configure_logging, export
import podman, prepare_virglrenderer, prepare_llama_cpp
from projects.remote.lib import remote_access

def _run(base_work_dir, cmd, env={}, check=True, capture_stdout=False, machine=True, get_command=False, print_cmd=False, log_dirname=None):
    podman_cmd = podman.get_podman_command()

    cmd = f"{podman_cmd} {'machine' if machine else ''} {cmd}"
    if get_command:
        return cmd

    if log_dirname:
        with env.NextArtifactDir(log_dirname):
            with open(env.ARTIFACT_DIR / "command.txt", "w") as f:
                print(cmd, file=f)
                print("", file=f)

                for k, v in env:
                    print(f"{k}={v}", file=f)

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
        env["VIRGL_APIR_BACKEND_LIBRARY"] = llama_remoting_backend_build_dir / config.project.get_config("prepare.podman.machine.remoting_env.ggml_libs[0]")
        env["APIR_LLAMA_CPP_GGML_LIBRARY_PATH"] = llama_remoting_backend_build_dir / config.project.get_config("prepare.podman.machine.remoting_env.ggml_libs[1]")
        env["VIRGL_ROUTE_VENUS_TO_APIR"] = "1"

        env |= config.project.get_config("prepare.podman.machine.remoting_env.env")
        env |= config.project.get_config("prepare.podman.machine.remoting_env.env_extra")

        prepare_virglrenderer.configure(base_work_dir, use_custom=True)
    else:
        prepare_virglrenderer.configure(base_work_dir, use_custom=False)

    ret = _run(base_work_dir, f"start {name} --no-info", env, print_cmd=True, log_dirname="start_podman_machine")

    if use_remoting and config.project.get_config("prepare.podman.machine.remoting_env.enabled"):
        if not config.project.get_config("prepare.virglrenderer.enabled"):
            logging.warning("The custom virglrenderer isn't enabled ...")

        if not prepare_virglrenderer.has_custom_virglrenderer(base_work_dir):
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
        if inspect_cmd.returncode == 127:
            logging.info("podman_machine: inspect: podman binary not found")
        elif "VM does not exist" in inspect_cmd.stdout:
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

    use_remoting = config.project.get_config("prepare.podman.machine.remoting_env.enabled")

    if (not was_stopped) and use_remoting and not prepare_virglrenderer.has_custom_virglrenderer(base_work_dir):
        logging.info("podman machine running with the wrong virglrenderer library. Stopping it.")
        force_restart = True

    force_restart = force_restart or config.project.get_config("prepare.podman.machine.force_configuration")

    if not was_stopped and force_restart:
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
