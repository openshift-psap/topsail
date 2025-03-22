import os
import pathlib
import logging
import tempfile

from projects.core.library import env, config, run, configure_logging, export
from projects.matrix_benchmarking.library import visualize

import podman as podman_mod
import remote_access, utils


def prepare_test(base_work_dir, platform):
    # nothing to do here
    pass


def _get_binary_path(base_work_dir, platform):
    version = config.project.get_config("prepare.ollama.repo.version")
    arch = config.project.get_config("remote_host.arch")

    system_file = config.project.get_config(f"prepare.ollama.repo.{platform.system}.file")

    dest = base_work_dir / f"ollama-{platform.system}-{version}" / system_file

    ollama_path = dest

    return ollama_path, dest, version


def get_binary_path(base_work_dir, platform):
    error_msg = utils.check_expected_platform(platform, system="macos", inference_server_name="ollama", needs_podman=False)
    if error_msg:
        raise ValueError(f"ollama.get_binary_path: unexpected platform: {error_msg} :/")

    ollama_path, _, _  = _get_binary_path(base_work_dir, platform)

    return ollama_path


def prepare_binary(base_work_dir, platform):
    ollama_path, dest, version = _get_binary_path(base_work_dir, platform)
    system_file = dest.name

    if remote_access.exists(ollama_path):
        logging.info(f"ollama {platform.name} already exists, not downloading it.")
        return ollama_path

    source = "/".join([
        config.project.get_config("prepare.ollama.repo.url"),
        "releases/download",
        version,
        system_file
    ])

    run.run_toolbox(
        "remote", "download",
        source=source, dest=dest,
        executable=True,
    )

    return ollama_path


def has_model(base_work_dir, ollama_path, model_name):
    # tell if the model is available locally

    ret = remote_access.run_with_ansible_ssh_conf(
        base_work_dir,
        f"{ollama_path} show {model_name}",
        check=False
    )

    return ret.returncode == 0


def pull_model(base_work_dir, ollama_path, model_name):
    remote_access.run_with_ansible_ssh_conf(
        base_work_dir,
        f"{ollama_path} pull {model_name} 2>/dev/null"
    )


def start_server(base_work_dir, ollama_path, stop=False):
    artifact_dir_suffix = None
    if stop:
        logging.info("Stopping the ollama server ...")
        artifact_dir_suffix = "_stop"

    run.run_toolbox(
        "mac_ai", "remote_ollama_start",
        base_work_dir=base_work_dir,
        path=ollama_path,
        port=config.project.get_config("test.inference_server.port"),
        stop=stop,
        mute_stdout=stop,
        artifact_dir_suffix=artifact_dir_suffix,
    )


def stop_server(base_work_dir, ollama_path):
    start_server(base_work_dir, ollama_path, stop=True)


def run_model(base_work_dir, ollama_path, model, unload=False):
    artifact_dir_suffix=None
    if unload:
        logging.info("Unloading the model from ollama server ...")
        artifact_dir_suffix = "_unload"

    run.run_toolbox(
        "mac_ai", "remote_ollama_run_model",
        base_work_dir=base_work_dir,
        path=ollama_path,
        name=model,
        unload=unload,
        mute_stdout=unload,
        artifact_dir_suffix=artifact_dir_suffix,
    )

    return model

def unload_model(base_work_dir, ollama_path, model, platform):
    remote_access.run_with_ansible_ssh_conf(
        base_work_dir,
        f"{ollama_path} stop {model}",
        check=False,
    )


def run_benchmark(base_work_dir, inference_server_path, model_fname):
    # no internal benchmark to run
    pass
