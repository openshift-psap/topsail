import logging
from projects.core.library import config
from container_engine import podman_machine
import remote_access
import install
import utils


def cleanup():
    if config.project.get_config("cleanup.podman_machine.delete"):
        machine = podman_machine()
        is_running = machine.is_running()
        if is_running:
            machine.stop()
        if is_running is not None:
            machine.rm()
            if config.project.get_config("cleanup.podman_machine.reset"):
                machine.reset()

    if config.project.get_config("cleanup.files.podman"):
        utils.cleanup_podman_files(remote_access.prepare())
    return 0


def prepare():
    logging.info("Preparing the environment:")
    base_work_dir = remote_access.prepare()

    if config.project.get_config("prepare.podman.repo.enabled"):
        utils.prepare_podman_from_gh_binary(base_work_dir)
        utils.prepare_gv_from_gh_binary(base_work_dir)

    logging.info("installing dependencies ...")
    install.dependencies(base_work_dir)

    logging.info("preparing podman machine ...")
    machine = podman_machine()
    machine.configure_and_start(force_restart=True)

    logging.info("preparing docker ...")
    # TODO: install docker

    # TODO: cleanup podman and docker

    return 0
