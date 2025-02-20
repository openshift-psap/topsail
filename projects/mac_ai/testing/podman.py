import os
import pathlib
import logging

from projects.core.library import env, config, run, configure_logging, export
import remote_access

def get_podman_binary():
    podman_bin = config.project.get_config("remote_host.podman_bin", print=False) or "podman"

    base_work_dir = remote_access.prepare()
    podman_env = dict(HOME=base_work_dir)


    if config.project.get_config("prepare.podman.machine.enabled", print=False):
        machine_name = config.project.get_config("prepare.podman.machine.name", print=False)
        podman_bin = f"{podman_bin} --connection '{machine_name}'"

        podman_env |= config.project.get_config("prepare.podman.machine.env", print=False)

    env_values = " ".join(f"'{k}={v}'" for k, v in (podman_env).items())
    env_cmd = f"env {env_values}"

    podman_bin = f"{env_cmd} {podman_bin} --connection '{machine_name}'"

    return podman_bin


def test(base_work_dir):
    podman_bin = get_podman_binary()
    image = config.project.get_config("prepare.podman.container.image")

    python_bin = config.project.get_config("prepare.podman.container.python_bin")
    remote_access.run_with_ansible_ssh_conf(
        base_work_dir,
        f"{podman_bin} run --entrypoint= --rm {image} {python_bin} --version",
    )


def start(base_work_dir, container_name, port):
    stop(base_work_dir, container_name)

    image = config.project.get_config("prepare.podman.container.image")
    podman_bin = get_podman_binary()

    platform = config.project.get_config("test.platform")

    podman_device_cmd = ""
    if "no-gpu" in platform:
        pass
    elif podman_device := config.project.get_config("prepare.podman.container.device"):
        podman_device_cmd = f"--device {podman_device} "

    command = (
        f"{podman_bin} run "
        f"--user root:root --cgroupns host --security-opt label=disable "
        f"-v{base_work_dir}:{base_work_dir}:Z "
        f"-w {base_work_dir} "
        f"--name {container_name} "
        f"--env OLLAMA_HOST=0.0.0.0:{port} "
        f"--env 'HOME={base_work_dir}' "
        f"-p {port}:{port} "
        + podman_device_cmd +
        "--detach --replace --rm --entrypoint= "
        f"{image} "
        "sleep inf"
    )

    with env.NextArtifactDir("start_podman"):
        with open(env.ARTIFACT_DIR / "command.txt", "w") as f:
            print(command, file=f)

        remote_access.run_with_ansible_ssh_conf(base_work_dir, command)


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
