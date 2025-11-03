import logging

from container_engine import PodmanMachine, ContainerEngine, DockerDesktopMachine
from config_manager import ConfigManager
import remote_access
import install
import utils


def cleanup():
    cleanup_config = ConfigManager.get_extended_cleanup_config()

    if cleanup_config['files_exec_time']:
        logging.info("Cleaning up exec_time script")
        base_work_dir = remote_access.prepare()
        exec_time_script = utils.get_benchmark_script_path(base_work_dir)
        if remote_access.exists(exec_time_script):
            logging.info(f"Removing {exec_time_script} ...")
            remote_access.remove_remote_file(base_work_dir, exec_time_script)

    if cleanup_config['files_venv']:
        logging.info("Cleaning up virtual environment")
        base_work_dir = remote_access.prepare()
        venv_path = utils.get_benchmark_script_path(base_work_dir).parent / ".venv"
        if remote_access.exists(venv_path):
            logging.info(f"Removing {venv_path} ...")
            remote_access.remove_remote_file(base_work_dir, venv_path, recursive=True)

    try:
        cleanup_podman_platform()
    except Exception as e:
        logging.error(f"Error during Podman platform cleanup: {e}")

    if cleanup_config['files_podman']:
        logging.info("Cleaning up Podman files")
        utils.cleanup_podman_files(remote_access.prepare())

    if cleanup_config['container_images']:
        logging.info("Cleaning up container images")
        utils.cleanup_container_images(remote_access.prepare())

    cleanup_docker_platform()
    return 0


def cleanup_podman_platform():
    cleanup_config = ConfigManager.get_extended_cleanup_config()
    if (
        not ConfigManager.is_linux() and
        cleanup_config['podman_machine_delete']
    ):
        logging.info("Cleaning up Podman machine")
        machine = PodmanMachine()
        is_running = machine.is_running()
        if is_running:
            machine.stop()
        machine.rm()


def cleanup_docker_platform():
    cleanup_config = ConfigManager.get_extended_cleanup_config()
    if (
        ConfigManager.is_linux() and
        cleanup_config['docker_service_stop']
    ):
        utils.docker_service("stop")
        return
    if (
        ConfigManager.is_docker_enabled() and
        cleanup_config['docker_desktop_stop']
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

    podman_config = ConfigManager.get_podman_config()
    custom_binary_config = ConfigManager.get_custom_binary_config()

    if podman_config['repo_enabled']:
        utils.prepare_podman_from_gh_binary(base_work_dir)

    if custom_binary_config['enabled']:
        utils.prepare_custom_podman_binary(base_work_dir)

    return 0


def prepare_docker_platform():
    remote_access.prepare()
    if not ConfigManager.is_docker_enabled():
        return 0

    if ConfigManager.is_linux():
        utils.docker_service("start")
    else:
        logging.info("preparing docker desktop")
        docker_desktop = DockerDesktopMachine()
        docker_desktop.start()

    docker = ContainerEngine("docker")
    docker.store_container_images_as_tar()
    docker.cleanup()


def prepare_windows_env_vars_podman():
    # Set environment variables for Podman on Windows
    # This is needed for the Podman machine to work correctly with the right provider (e.g., wsl, hyperv).
    # Because machine is started in a new shell, we need to set these variables permanently to survive
    # the exit of ssh session.
    home = remote_access.prepare()
    logging.info("Setting environment variables for Podman on Windows")
    machine_config = ConfigManager.get_podman_machine_config()
    provider = machine_config['env_containers_machine_provider']

    # Cast to string and escape/remove internal quotes, then wrap in quotes for setx
    provider_str = str(provider).replace('"', '')
    home_str = str(home).replace('"', '')

    remote_access.run_with_ansible_ssh_conf(home, f'setx CONTAINERS_MACHINE_PROVIDER "{provider_str}"')
    remote_access.run_with_ansible_ssh_conf(home, f'setx HOME "{home_str}"')


def prepare_podman_platform():
    remote_access.prepare()
    podman_config = ConfigManager.get_podman_config()

    if ConfigManager.is_linux():
        if podman_config['repo_enabled']:
            logging.info("Build Podman from GitHub repository")
            utils.build_podman_from_gh_binary()
    else:
        logging.info("preparing podman machine")
        if ConfigManager.is_windows():
            prepare_windows_env_vars_podman()

        machine = PodmanMachine()
        if not machine.is_running():
            machine.configure_and_start(
                force_restart=True,
                configure=ConfigManager.should_use_podman_machine_configuration()
            )

    logging.info("cleaning up podman")
    podman = ContainerEngine("podman")
    podman.store_container_images_as_tar()
    podman.cleanup()

    return 0
