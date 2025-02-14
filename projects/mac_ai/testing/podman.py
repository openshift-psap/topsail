import os
import pathlib
import logging

from projects.core.library import env, config, run, configure_logging, export
import remote_access

def get_podman_binary():
    podman_bin = config.project.get_config("remote_host.podman_bin", print=False) or "podman"

    if config.project.get_config("prepare.podman.machine.enabled", print=False):
        machine_name = config.project.get_config("prepare.podman.machine.name", print=False)
        podman_bin = f"{podman_bin} --connection '{machine_name}'"

    return podman_bin


def test(base_work_dir):
    podman_bin = get_podman_binary()
    image = config.project.get_config("prepare.podman.container.image")

    python_bin = config.project.get_config("prepare.podman.container.python_bin")
    remote_access.run_with_ansible_ssh_conf(
        base_work_dir,
        f"{podman_bin} run --rm {image} {python_bin} --version",
    )


def start(base_work_dir, container_name, port):
    stop(base_work_dir, container_name)

    image = config.project.get_config("prepare.podman.container.image")
    podman_bin = get_podman_binary()

    remote_access.run_with_ansible_ssh_conf(
        base_work_dir,
        f"{podman_bin} run "
        f"--user root:root --cgroupns host --security-opt label=disable "
        f"-v{base_work_dir}:{base_work_dir}:Z "
        f"-w {base_work_dir} "
        f"--name {container_name} "
        f"--env OLLAMA_HOST=0.0.0.0:{port} "
        f"--env 'HOME={base_work_dir}' "
        f"-p {port}:{port} "
        "--detach --replace --rm "
        f"{image} "
        "sleep inf"
    )

def stop(base_work_dir, container_name):
    podman_bin = get_podman_binary()

    name = config.project.get_config("prepare.podman.container.name")
    remote_access.run_with_ansible_ssh_conf(
        base_work_dir,
        f"{podman_bin} rm --force --time 0 {container_name}", check=False
    )

def get_exec_command_prefix(container_name):
    podman_bin = get_podman_binary()

    return f"{podman_bin} exec -it {container_name}"
