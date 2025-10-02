import logging
from projects.core.library import config
from container_engine import PodmanMachine, ContainerEngine, DockerDesktopMachine
import remote_access
import install
import utils


def cleanup():
    if config.project.get_config("cleanup.files.exec_time"):
        logging.info("Cleaning up exec_time script")
        base_work_dir = remote_access.prepare()
        exec_time_script = utils.get_benchmark_script_path(base_work_dir)
        if remote_access.exists(exec_time_script):
            logging.info(f"Removing {exec_time_script} ...")
            remote_access.run_with_ansible_ssh_conf(base_work_dir, f"rm -f {exec_time_script}")

    if config.project.get_config("cleanup.files.venv"):
        logging.info("Cleaning up virtual environment")
        base_work_dir = remote_access.prepare()
        venv_path = utils.get_benchmark_script_path(base_work_dir).parent / ".venv"
        if remote_access.exists(venv_path):
            logging.info(f"Removing {venv_path} ...")
            remote_access.run_with_ansible_ssh_conf(base_work_dir, f"rm -rf {venv_path}")

    try:
        cleanup_podman_platform_darwin()
    except Exception as e:
        logging.error(f"Error during Podman platform cleanup: {e}")

    if config.project.get_config("cleanup.files.podman"):
        logging.info("Cleaning up Podman files")
        utils.cleanup_podman_files(remote_access.prepare())

    cleanup_docker_platform_darwin()
    return 0


def cleanup_podman_platform_darwin():
    if config.project.get_config("cleanup.podman_machine.delete"):
        logging.info("Cleaning up Podman machine")
        machine = PodmanMachine()
        is_running = machine.is_running()
        if is_running:
            machine.stop()
        machine.rm()


def cleanup_docker_platform_darwin():
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
        utils.prepare_gv_from_gh_binary(base_work_dir)

    if config.project.get_config("prepare.podman.custom_binary.enabled", print=False):
        utils.prepare_custom_podman_binary(base_work_dir)

    return 0


def prepare_docker_platform_darwin():
    if config.project.get_config("remote_host.docker.enabled", print=False):
        logging.info("preparing docker desktop")
        docker_desktop = DockerDesktopMachine()
        docker_desktop.start()
        docker = ContainerEngine("docker")
        docker.cleanup()


def prepare_podman_platform_darwin():
    logging.info("preparing podman machine")
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
