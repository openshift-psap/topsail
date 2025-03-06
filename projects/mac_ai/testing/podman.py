import os
import pathlib
import logging

from projects.core.library import env, config, run, configure_logging, export
import remote_access

def prepare_gv_from_gh_binary(base_work_dir):

    podman_path, version = _get_repo_podman_path(base_work_dir)
    gvisor_path = podman_path.parent.parent / "libexec" / "podman" / "gvproxy"

    if remote_access.exists(gvisor_path):
        logging.info(f"gvproxy exists, not downloading it.")
        return

    system = config.project.get_config("remote_host.system")
    src_file = config.project.get_config(f"prepare.podman.gvisor.repo.file")

    source = "/".join([
        config.project.get_config("prepare.podman.gvisor.repo.url"),
        "releases/download",
        config.project.get_config(f"prepare.podman.gvisor.repo.version"),
        src_file,
    ])

    run.run_toolbox(
        "remote", "download",
        source=source,
        dest=gvisor_path,
        executable=True,
    )

def prepare_from_gh_binary(base_work_dir):
    arch = config.project.get_config("remote_host.arch")
    system = config.project.get_config("remote_host.system")

    podman_path, version = _get_repo_podman_path(base_work_dir)

    if remote_access.exists(podman_path):
        logging.info(f"podman {version} already exists, not downloading it.")
        return podman_path

    zip_file = config.project.get_config(f"prepare.podman.repo.{system}.file")

    source = "/".join([
        config.project.get_config("prepare.podman.repo.url"),
        "releases/download",
        config.project.get_config(f"prepare.podman.repo.version"),
        zip_file,
    ])

    dest = base_work_dir / f"podman-{version}" / zip_file

    run.run_toolbox(
        "remote", "download",
        source=source,
        dest=dest,
        zip=True,
    )



    return podman_path


def _get_repo_podman_path(base_work_dir):
    system = config.project.get_config(f"remote_host.system", print=False)
    version = config.project.get_config(f"prepare.podman.repo.version", print=False)

    podman_path = base_work_dir / f"podman-{version}" / "usr" / "bin" / "podman"

    return podman_path, version


def get_podman_binary():
    base_work_dir = remote_access.prepare()

    system = config.project.get_config("remote_host.system", print=False)
    if config.project.get_config(f"prepare.podman.repo.enabled", print=False):
        podman_bin, _ = _get_repo_podman_path(base_work_dir)
    else:
        podman_bin = config.project.get_config("remote_host.podman_bin", print=False) or "podman"

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


def start(base_work_dir, port):
    container_name = config.project.get_config("prepare.podman.container.name", print=False)

    stop(base_work_dir)

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

        return remote_access.run_with_ansible_ssh_conf(base_work_dir, command)


def stop(base_work_dir, check=False):
    podman_bin = get_podman_binary()

    container_name = config.project.get_config("prepare.podman.container.name", print=False)
    return remote_access.run_with_ansible_ssh_conf(
        base_work_dir,
        f"{podman_bin} rm --force --time 0 {container_name}", check=check,
    )


def get_exec_command_prefix():
    container_name = config.project.get_config("prepare.podman.container.name", print=False)
    podman_bin = get_podman_binary()

    return f"{podman_bin} exec -it {container_name}"
