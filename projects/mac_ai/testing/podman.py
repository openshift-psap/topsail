import os, sys
import pathlib
import logging
import yaml
import json

from projects.core.library import env, config, run, configure_logging, export
import utils, prepare_release
from projects.remote.lib import remote_access

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
        artifact_dir_suffix="__gvproxy",
    )


def which_podman(base_work_dir, podman_path):
    ret = remote_access.run_with_ansible_ssh_conf(
            base_work_dir,
            f"which '{podman_path}'",
            capture_stdout=True,
            check=False,
        )

    if ret.returncode != 0:
        return None

    return ret.stdout.strip()


def prepare_from_gh_binary(base_work_dir):
    arch = config.project.get_config("remote_host.arch")
    system = config.project.get_config("remote_host.system")

    podman_path, version = _get_repo_podman_path(base_work_dir)

    if remote_access.exists(podman_path):
        logging.info(f"podman {version} already exists, not downloading it.")
        return podman_path

    if not config.project.get_config("prepare.podman.repo.enabled", False):
        # already exists as a file covered above

        if not which_podman(base_work_dir, podman_path):
            msg = f"podman repo not enabled, but not found in the system ({podman_path}) :/"
            logging.error(msg)
            raise ValueError(msg)

        logging.info("podman found in the system, not downloading it")

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
        artifact_dir_suffix="__podman",
    )

    return podman_path


def _get_repo_podman_path(base_work_dir):
    version = config.project.get_config("prepare.podman.repo.version", print=False)

    podman_path = base_work_dir / f"podman-{version}" / f"podman-{version.removeprefix('v')}" / "usr" / "bin" / "podman"

    return podman_path, version


def get_podman_binary(base_work_dir):
    if config.project.get_config("prepare.podman.repo.enabled", print=False):
        podman_bin, _ = _get_repo_podman_path(base_work_dir)
    else:
        podman_bin = config.project.get_config("remote_host.podman_bin", print=False)
        if not podman_bin:
            podman_bin = remote_access.run_with_ansible_ssh_conf(
                base_work_dir, "which podman", capture_stdout=True, check=False).stdout.strip()
            if not podman_bin:
                raise ValueError("podman not found in the PATH")

        podman_bin = pathlib.Path(podman_bin)

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


def pull_image(base_work_dir, image):
    podman_cmd = get_podman_command()

    ret = remote_access.run_with_ansible_ssh_conf(
        base_work_dir,
        f"{podman_cmd} image pull {image}",
    )

    return ret.returncode == 0


def inspect_image(base_work_dir, image):
    podman_cmd = get_podman_command()

    ret = remote_access.run_with_ansible_ssh_conf(
        base_work_dir,
        f"{podman_cmd} image inspect {image}",
        check=True,
        capture_stdout=True,
        capture_stderr=True,
    )

    return json.loads(ret.stdout)


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


def run_container(base_work_dir, image, volumes=None, user=":", command=""):
    podman_cmd = get_podman_command()

    volumes_str = ''
    if volumes:
        volumes_str = " ".join([f"-v '{key}:{value}:Z'" for key, value in volumes.items()])

    remote_access.run_with_ansible_ssh_conf(
        base_work_dir,
        f"{podman_cmd} run --user '{user}' --pull=never --rm {volumes_str} '{image}' {command}",
    )


def start(base_work_dir, port, get_command=None):
    container_name = config.project.get_config("prepare.podman.container.name", print=False)
    system = config.project.get_config("remote_host.system")
    if system == "linux" and get_command is None:
        logging.info("Can't *start* podman on linux/krun ...")
        return

    stop(base_work_dir)

    image = config.project.get_config("prepare.podman.container.image")
    podman_cmd = get_podman_command()

    platform = utils.parse_platform(config.project.get_config("test.platform"))

    podman_device_cmd = ""
    if not platform.want_gpu:
        logging.info(f"podman.start: No GPU device for {platform}")

    elif podman_device := config.project.get_config("prepare.podman.container.device"):
        podman_device_cmd = f"--device {podman_device} "
        logging.info(f"podman.start: GPU device for {platform}: {podman_device}")
    else:
        logging.warn(f"podman.start: No GPU device configured")

    env_str = ""
    if system == "linux" and platform.inference_server_flavor == "remoting":
        env_str += " ".join([f"-e {k}={v}" for k, v in prepare_release.get_linux_remoting_pod_env(base_work_dir).items()])

    remoting_opts = ""
    if system == "linux" and config.project.get_config("prepare.podman.machine.remoting_env.enabled"):
        remoting_opts += "--runtime krun "

    command = (
        f"{podman_cmd} run "
        f"--user root:root --cgroupns host --security-opt label=disable "
        f"-v {base_work_dir}:{base_work_dir} "
        f"-w {base_work_dir} "
        f"--name {container_name} "
        f"--env 'HOME={base_work_dir}' "
        f"{env_str}  "
        f"-p {port}:{port} "
        f"{podman_device_cmd} "
        f"{remoting_opts}  "
        "--detach --replace --rm --entrypoint= "
        f"{image}"
    )

    if get_command:
        return command

    command += " sleep inf"

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
    system = config.project.get_config("remote_host.system")
    if system == "linux":
        return _get_krun_exec_command_prefix()

    return f"{podman_cmd} exec -it {container_name}"


def _get_krun_exec_command_prefix():
    base_work_dir = remote_access.prepare()
    inference_server_port = config.project.get_config("test.inference_server.port")

    return start(base_work_dir, inference_server_port, get_command=True).replace("--detach", "")


def login(base_work_dir, credentials_key):
    creds_str = config.project.get_config(credentials_key, handled_secretly=True)
    creds = yaml.safe_load(creds_str)
    podman_bin = get_podman_binary(base_work_dir)

    cmd = f"{podman_bin} login --username '{creds['login']}' --password '{creds['password']}' '{creds['server']}'"
    remote_access.run_with_ansible_ssh_conf(base_work_dir, cmd, handled_secretly=True)


def push_image(base_work_dir, local_name, remote_name):
    podman_bin = get_podman_binary(base_work_dir)
    cmd = f"{podman_bin} push {local_name} {remote_name}"

    remote_access.run_with_ansible_ssh_conf(base_work_dir, cmd)

def write_authfile(base_work_dir, content):
    authfile = base_work_dir / ".config/containers/auth.json"
    remote_access.mkdir(authfile.parent)
    remote_access.write(authfile, content, handled_secretly=True)
    remote_access.run_with_ansible_ssh_conf(
        base_work_dir,
        f"chmod 600 '{base_work_dir}/.config/containers/auth.json'",
        handled_secretly=True,
    )
