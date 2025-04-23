import os
import pathlib
import logging

from projects.core.library import env, config, run, configure_logging, export
import remote_access, utils


def cleanup(base_work_dir):
    version = config.project.get_config("prepare.podman.repo.version", print=False)

    dest = base_work_dir / f"podman-{version}"

    if not remote_access.exists(dest):
        logging.info(f"{dest} does not exists, nothing to remove.")
        return

    logging.info(f"Removing {dest} ...")
    remote_access.run_with_ansible_ssh_conf(base_work_dir, f"rm -rf {dest}")


def prepare_gv_from_gh_binary(base_work_dir):

    podman_path, version = _get_repo_podman_path(base_work_dir)
    gvisor_path = podman_path.parent.parent / "libexec" / "podman" / "gvproxy"

    if remote_access.exists(gvisor_path):
        logging.info("gvproxy exists, not downloading it.")
        return

    src_file = config.project.get_config("prepare.podman.gvisor.repo.file")

    source = "/".join([
        config.project.get_config("prepare.podman.gvisor.repo.url"),
        "releases/download",
        config.project.get_config("prepare.podman.gvisor.repo.version"),
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
        config.project.get_config("prepare.podman.repo.version"),
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
    version = config.project.get_config("prepare.podman.repo.version", print=False)

    podman_path = base_work_dir / f"podman-{version}" / "usr" / "bin" / "podman"

    return podman_path, version


def get_podman_binary(base_work_dir):
    if config.project.get_config("prepare.podman.repo.enabled", print=False):
        podman_bin, _ = _get_repo_podman_path(base_work_dir)
    else:
        podman_bin = config.project.get_config("remote_host.podman_bin", print=False) or "podman"

    return podman_bin


def get_podman_env(base_work_dir):
    podman_env = dict(HOME=base_work_dir)

    if config.project.get_config("prepare.podman.machine.enabled", print=False):
        podman_env |= config.project.get_config("prepare.podman.machine.env", print=False)

    return podman_env


def get_podman_command():
    base_work_dir = remote_access.prepare()

    podman_cmd = get_podman_binary(base_work_dir)
    podman_env = get_podman_env(base_work_dir)

    if config.project.get_config("prepare.podman.machine.enabled", print=False):
        machine_name = config.project.get_config("prepare.podman.machine.name", print=False)
        podman_cmd = f"{podman_cmd} --connection '{machine_name}'"

    env_values = " ".join(f"'{k}={v}'" for k, v in (podman_env).items())
    env_cmd = f"env {env_values}"

    podman_cmd = f"{env_cmd} {podman_cmd}"

    return podman_cmd


def test(base_work_dir):
    podman_cmd = get_podman_command()
    image = config.project.get_config("prepare.podman.container.image")

    python_bin = config.project.get_config("prepare.podman.container.python_bin")
    remote_access.run_with_ansible_ssh_conf(
        base_work_dir,
        f"{podman_cmd} run --entrypoint= --rm {image} {python_bin} --version",
    )


def has_image(base_work_dir, image):
    podman_cmd = get_podman_command()

    ret = remote_access.run_with_ansible_ssh_conf(
        base_work_dir,
        f"{podman_cmd} image inspect {image}",
        check=False,
        capture_stdout=True,
        capture_stderr=True,
    )

    return ret.returncode == 0


def rm_image(base_work_dir, image):
    podman_cmd = get_podman_command()

    ret = remote_access.run_with_ansible_ssh_conf(
        base_work_dir,
        f"{podman_cmd} image rm {image}",
        check=False,
        capture_stdout=True,
        capture_stderr=True,
    )

    return ret.returncode == 0


def start(base_work_dir, port):
    container_name = config.project.get_config("prepare.podman.container.name", print=False)

    stop(base_work_dir)

    image = config.project.get_config("prepare.podman.container.image")
    podman_cmd = get_podman_command()

    platform = utils.parse_platform(config.project.get_config("test.platform"))

    podman_device_cmd = ""
    if not platform.want_gpu:
        logging.info(f"podman.start: No GPU device for {platform}")
        pass
    elif podman_device := config.project.get_config("prepare.podman.container.device"):
        podman_device_cmd = f"--device {podman_device} "
        logging.info(f"podman.start: GPU device for {platform}: {podman_device}")
    else:
        logging.warn(f"podman.start: No GPU device configured")

    command = (
        f"{podman_cmd} run "
        f"--user root:root --cgroupns host --security-opt label=disable "
        f"-v{base_work_dir}:{base_work_dir}:Z "
        f"-w {base_work_dir} "
        f"--name {container_name} "
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
    podman_cmd = get_podman_command()

    container_name = config.project.get_config("prepare.podman.container.name", print=False)
    return remote_access.run_with_ansible_ssh_conf(
        base_work_dir,
        f"{podman_cmd} rm --force --time 0 {container_name}", check=check,
    )


def get_exec_command_prefix():
    container_name = config.project.get_config("prepare.podman.container.name", print=False)
    podman_cmd = get_podman_command()

    return f"{podman_cmd} exec -it {container_name}"
