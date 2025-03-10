#!/usr/bin/env python3

import os, sys
import pathlib
import logging
import tempfile
import subprocess

import fire

from projects.core.library import env, config, run, configure_logging, export
from projects.matrix_benchmarking.library import visualize

import podman as podman_mod
import remote_access, podman_machine
from entrypoint import entrypoint

TESTING_THIS_DIR = pathlib.Path(__file__).absolute().parent


def pull_model(base_work_dir, llama_cpp_path, model, dest):
    llama_cpp_path = llama_cpp_path.parent / 'llama-run'

    return run.run_toolbox(
        "mac_ai", "remote_llama_cpp_pull_model",
        base_work_dir=base_work_dir,
        path=llama_cpp_path,
        name=model,
        dest=dest,
    )


def run_model(base_work_dir, llama_cpp_path, model):
    inference_server_port = config.project.get_config("test.inference_server.port")
    # dirty, I know ...
    prefix, _, path = str(llama_cpp_path).rpartition(" ")
    run.run_toolbox(
        "mac_ai", "remote_llama_cpp_run_model",
        base_work_dir=base_work_dir,
        prefix=prefix,
        path=path,
        name=model,
        port=inference_server_port,
    )


def unload_model(base_work_dir, llama_cpp_path, model, use_podman=False):
    if use_podman:
        podman_prefix = podman_mod.get_exec_command_prefix()
        command = f"{podman_prefix} pkill python"
    else:
        command = f"pkill llama-server"

    remote_access.run_with_ansible_ssh_conf(
        base_work_dir,
        command,
        check=False,
    )

# ---

@entrypoint()
def rebuild_image(start=True):
    base_work_dir = remote_access.prepare()
    prepare_test(base_work_dir, use_podman=True)

    try:
        cleanup_image(base_work_dir)
    except subprocess.CalledProcessError as e:
        if e.returncode == 1:
            logging.info("Couldn't delete the image: image not known. Ignoring.")
            return

        raise e

    prepare_podman_image_from_local_container_file(base_work_dir)

    if start:
        return start_podman()

    return 0


@entrypoint()
def start_podman():
    base_work_dir = remote_access.prepare()

    prepare_test(base_work_dir, use_podman=True)

    inference_server_port = config.project.get_config("test.inference_server.port")
    podman_container_name = config.project.get_config("prepare.podman.container.name")
    return podman_mod.start(base_work_dir, podman_container_name, inference_server_port).returncode


class Entrypoint:
    """
    Commands for launching the llama-cpp helper commands
    """

    def __init__(self):
        self.rebuild_image = rebuild_image
        self.start_podman = start_podman

# ---

def main():
    # Print help rather than opening a pager
    fire.core.Display = lambda lines, out: print(*lines, file=out)

    fire.Fire(Entrypoint())


if __name__ == "__main__":
    try:
        sys.exit(main())
    except subprocess.CalledProcessError as e:
        logging.error(f"Command '{e.cmd}' failed --> {e.returncode}")
        sys.exit(1)
    except KeyboardInterrupt:
        print() # empty line after ^C
        logging.error(f"Interrupted.")
        sys.exit(1)
