#!/usr/bin/env python3

import os, sys
import pathlib
import logging
import tempfile
import subprocess

import fire

from projects.core.library import env, config, run, configure_logging, export
from projects.matrix_benchmarking.library import visualize

from projects.remote.lib import remote_access
import podman as podman_mod
import prepare_llama_cpp
from entrypoint import entrypoint
import utils

TESTING_THIS_DIR = pathlib.Path(__file__).absolute().parent

def _model_name(model):
    return model.split("/")[-1]

def start_server(base_work_dir, platform, llama_cpp_path):
    pass # nothing to start


def stop_server(base_work_dir, platform, llama_cpp_path):
    pass # nothing to stop


def has_model(base_work_dir, platform, llama_cpp_path, model):
    model_fname = utils.model_to_fname(_model_name(model))

    return remote_access.exists(model_fname)


def pull_model(base_work_dir, platform, llama_cpp_path, model):
    llama_cpp_path = llama_cpp_path.replace("llama-server", "llama-run")
    model_name = _model_name(model)
    model_fname = utils.model_to_fname(model_name)

    return run.run_toolbox(
        "mac_ai", "remote_llama_cpp_pull_model",
        base_work_dir=base_work_dir,
        path=llama_cpp_path,
        name=model,
        dest=model_fname,
    )


def run_model(base_work_dir, platform, llama_cpp_path, model):
    inference_server_port = config.project.get_config("test.inference_server.port")
    model_fname = utils.model_to_fname(_model_name(model))

    # dirty, I know ...
    prefix, _, path = str(llama_cpp_path).rpartition(" ")
    run.run_toolbox(
        "mac_ai", "remote_llama_cpp_run_model",
        base_work_dir=base_work_dir,
        prefix=prefix,
        path=path,
        name=model_fname,
        port=inference_server_port,
    )

    return model_fname


def unload_model(base_work_dir, platform, llama_cpp_path, model):
    system = config.project.get_config("remote_host.system")

    if platform.needs_podman:
        if system == "linux":
            logging.info("Can't *unload* the model on linux/krun. Stopping the container.")
            podman_mod.stop(base_work_dir)
            return
        else:
            podman_prefix = podman_mod.get_exec_command_prefix()
            command = f"{podman_prefix} pkill python"
    else:
        command = f"pkill llama-server"

    remote_access.run_with_ansible_ssh_conf(
        base_work_dir,
        command,
        check=False,
    )


def run_benchmark(base_work_dir, platform, llama_cpp_path, model):
    model_fname = utils.model_to_fname(_model_name(model))

    # dirty, I know ...
    prefix, _, path = str(llama_cpp_path).rpartition(" ")
    path = path.replace("llama-server", "")

    do_llama_bench = config.project.get_config("test.inference_server.benchmark.llama_cpp.llama_bench")
    do_test_backend_ops = config.project.get_config("test.inference_server.benchmark.llama_cpp.backend_ops_perf")

    if not (do_llama_bench or do_test_backend_ops):
        logging.warning("run_benchmark: inference server benchmark enabled, but llama_cpp test enabled...")
        return

    run.run_toolbox(
        "mac_ai", "remote_llama_cpp_run_bench",
        path=path.rstrip("/"),
        prefix=prefix,
        model_name=model_fname,
        llama_bench=do_llama_bench,
        test_backend_ops=do_test_backend_ops,
    )

# ---

@entrypoint()
def rebuild_image(start=True):
    base_work_dir = remote_access.prepare()
    prepare_llama_cpp.prepare_test(base_work_dir, utils.parse_platform("macos/llama_cpp/upstream_bin"))

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

    prepare_llama_cpp.prepare_test(base_work_dir, utils.parse_platform("macos/llama_cpp/upstream_bin"))

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
