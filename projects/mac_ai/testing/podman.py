import os
import pathlib
import logging

from projects.core.library import env, config, run, configure_logging, export
import remote_access

def test():
    image = config.project.get_config("prepare.podman.image")
    remote_access.run_with_ansible_ssh_conf(f"podman run -it {image} python --version")

def start(base_work_dir, container_name, port):
    stop(container_name)

    image = config.project.get_config("prepare.podman.image")

    remote_access.run_with_ansible_ssh_conf(
        f"podman run "
        f"--user root:root --cgroupns host --security-opt label=disable "
        f"-v{base_work_dir}:{base_work_dir}:Z "
        f"-w {base_work_dir} "
        f"--name {container_name} "
        f"--env OLLAMA_HOST=0.0.0.0:{port} "
        f"-v$HOME:$HOME "
        f"--env HOME=$HOME "
        f"-p {port}:{port} "
        "--detach --replace --rm "
        f"{image} "
        "sleep inf"
    )

def stop(container_name):
    name = config.project.get_config("prepare.podman.container.name")
    remote_access.run_with_ansible_ssh_conf(f"podman rm --force --time 0 {container_name}", check=False)

def get_exec_command_prefix(container_name):
    return f"podman exec -it {container_name}"
