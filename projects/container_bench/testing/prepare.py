import logging
import shlex
from projects.core.library import config
from container_engine import PodmanMachine, ContainerEngine, DockerDesktopMachine
import remote_access
import install
import utils


def remove_remote_file(base_work_dir, file_path, recursive=False):
    """Remove a file or directory on the remote host, compatible with both Windows and Unix."""
    is_windows = config.project.get_config("remote_host.system", print=False) == "windows"

    if is_windows:
        flags = "-Force -ErrorAction SilentlyContinue"
        if recursive:
            flags += " -Recurse"
        cmd = f"Remove-Item '{file_path}' {flags}"
    else:
        flag = "-rf" if recursive else "-f"
        cmd = f"rm {flag} {shlex.quote(str(file_path))}"

    remote_access.run_with_ansible_ssh_conf(base_work_dir, cmd)


def cleanup():
    if config.project.get_config("cleanup.files.exec_time"):
        logging.info("Cleaning up exec_time script")
        base_work_dir = remote_access.prepare()
        exec_time_script = utils.get_benchmark_script_path(base_work_dir)
        if remote_access.exists(exec_time_script):
            logging.info(f"Removing {exec_time_script} ...")
            remove_remote_file(base_work_dir, exec_time_script)

    if config.project.get_config("cleanup.files.venv"):
        logging.info("Cleaning up virtual environment")
        base_work_dir = remote_access.prepare()
        venv_path = utils.get_benchmark_script_path(base_work_dir).parent / ".venv"
        if remote_access.exists(venv_path):
            logging.info(f"Removing {venv_path} ...")
            remove_remote_file(base_work_dir, venv_path, recursive=True)

    try:
        cleanup_podman_platform()
    except Exception as e:
        logging.error(f"Error during Podman platform cleanup: {e}")

    if config.project.get_config("cleanup.files.podman"):
        logging.info("Cleaning up Podman files")
        utils.cleanup_podman_files(remote_access.prepare())

    cleanup_docker_platform()
    return 0


def cleanup_podman_platform():
    if (
        config.project.get_config("remote_host.system", print=False) != "linux" and
        config.project.get_config("cleanup.podman_machine.delete")
    ):
        logging.info("Cleaning up Podman machine")
        machine = PodmanMachine()
        is_running = machine.is_running()
        if is_running:
            machine.stop()
        machine.rm()


def cleanup_docker_platform():
    if (
        config.project.get_config("remote_host.system", print=False) == "linux" and
        config.project.get_config("cleanup.docker_service.stop")
    ):
        utils.docker_service("stop")
        return
    if (
        config.project.get_config("remote_host.docker.enabled", print=False) and
        config.project.get_config("cleanup.docker_desktop.stop")
    ):
        logging.info("Stopping Docker Desktop")
        docker_desktop = DockerDesktopMachine()
        if docker_desktop.is_running():
            docker_desktop.stop()


def prepare():
    logging.info("Preparing the environment:")
    base_work_dir = remote_access.prepare()

    utils.prepare_benchmark_script(base_work_dir)

    logging.info("installing dependencies")
    install.dependencies(base_work_dir)

    if config.project.get_config("prepare.podman.repo.enabled"):
        utils.prepare_podman_from_gh_binary(base_work_dir)

    if config.project.get_config("prepare.podman.custom_binary.enabled", print=False):
        utils.prepare_custom_podman_binary(base_work_dir)

    return 0


def prepare_docker_platform():
    if not config.project.get_config("remote_host.docker.enabled", print=False):
        return 0

    if config.project.get_config("remote_host.system", print=False) == "linux":
        utils.docker_service("start")
    else:
        logging.info("preparing docker desktop")
        docker_desktop = DockerDesktopMachine()
        docker_desktop.start()

    docker = ContainerEngine("docker")
    docker.cleanup()


def prepare_windows_env_vars_podman():
    # Set environment variables for Podman on Windows
    # This is needed for the Podman machine to work correctly with the right provider (e.g., wsl, hyperv).
    # Because machine is started in a new shell, we need to set these variables permanently to survive
    # the exit of ssh session.
    logging.info("Setting environment variables for Podman on Windows")
    provider = config.project.get_config("prepare.podman.machine.env.CONTAINERS_MACHINE_PROVIDER", print=False)
    home = remote_access.prepare()

    # Cast to string and escape/remove internal quotes, then wrap in quotes for setx
    provider_str = str(provider).replace('"', '')
    home_str = str(home).replace('"', '')

    remote_access.run_with_ansible_ssh_conf(home, f'setx CONTAINERS_MACHINE_PROVIDER "{provider_str}"')
    remote_access.run_with_ansible_ssh_conf(home, f'setx HOME "{home_str}"')


def prepare_podman_platform():
    if config.project.get_config("remote_host.system", print=False) == "linux":
        if config.project.get_config("prepare.podman.repo.enabled"):
            logging.info("Build Podman from GitHub repository")
            utils.build_podman_from_gh_binary()
    else:
        logging.info("preparing podman machine")
        if config.project.get_config("remote_host.system", print=False) == "windows":
            prepare_windows_env_vars_podman()

        machine = PodmanMachine()
        if not machine.is_running():
            machine.configure_and_start(
                force_restart=True,
                configure=config.project.get_config("prepare.podman.machine.use_configuration", print=False)
            )

    logging.info("cleaning up podman")
    podman = ContainerEngine("podman")
    podman.cleanup()

    return 0
