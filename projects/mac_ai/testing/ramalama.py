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
    version = config.project.get_config("prepare.ramalama.repo.version")

    system_file = f"{version}.zip"

    # don't use 'ramalama' in the base_work_dir, otherwise Python
    # takes it (invalidly) for the package `ramalama` package
    dest = base_work_dir / "ramalama-ai" / system_file

    ramalama_path = dest.parent / f"ramalama-{version.removeprefix('v')}" / "bin" / "ramalama"

    return ramalama_path, dest, version


def get_binary_path(base_work_dir, platform):
    error_msg = utils.check_expected_platform(platform, system="podman", inference_server_name="ramalama", needs_podman=True)
    if error_msg:
        raise ValueError(f"ramalama.get_binary_path: unexpected platform: {error_msg} :/")

    ramalama_path, _, _  = _get_binary_path(base_work_dir, platform)

    return ramalama_path


def prepare_binary(base_work_dir, platform):
    ramalama_path, dest, version = _get_binary_path(base_work_dir, platform)
    system_file = dest.name

    if remote_access.exists(ramalama_path):
        logging.info(f"ramalama {platform.name} already exists, not downloading it.")
        return ramalama_path

    source = "/".join([
        config.project.get_config("prepare.ramalama.repo.url"),
        "archive/refs/tags",
        f"{version}.zip",
    ])

    run.run_toolbox(
        "remote", "download",
        source=source, dest=dest,
        tarball=True,
    )

    return ramalama_path


def has_model(base_work_dir, ramalama_path, model_name):
    # tell if the model is available locally

    ret = remote_access.run_with_ansible_ssh_conf(
        base_work_dir,
        f"{ramalama_path} show {model_name}",
        check=False
    )

    return ret.returncode == 0


def pull_model(base_work_dir, ramalama_path, model_name):
    remote_access.run_with_ansible_ssh_conf(
        base_work_dir,
        f"{ramalama_path} pull {model_name} 2>/dev/null"
    )


def start_server(base_work_dir, ramalama_path, stop=False):
    artifact_dir_suffix = None
    if stop:
        logging.info("Stopping the ramalama server ...")
        artifact_dir_suffix = "_stop"

    run.run_toolbox(
        "mac_ai", "remote_ramalama_start",
        base_work_dir=base_work_dir,
        path=ramalama_path,
        port=config.project.get_config("test.inference_server.port"),
        stop=stop,
        mute_stdout=stop,
        artifact_dir_suffix=artifact_dir_suffix,
    )


def stop_server(base_work_dir, ramalama_path):
    start_server(base_work_dir, ramalama_path, stop=True)


def run_model(base_work_dir, ramalama_path, model, unload=False):
    artifact_dir_suffix=None
    if unload:
        logging.info("Unloading the model from ramalama server ...")
        artifact_dir_suffix = "_unload"

    run.run_toolbox(
        "mac_ai", "remote_ramalama_run_model",
        base_work_dir=base_work_dir,
        path=ramalama_path,
        name=model,
        unload=unload,
        mute_stdout=unload,
        artifact_dir_suffix=artifact_dir_suffix,
    )

    return model

def unload_model(base_work_dir, ramalama_path, model, platform):
    remote_access.run_with_ansible_ssh_conf(
        base_work_dir,
        f"{ramalama_path} stop {model}",
        check=False,
    )


def run_benchmark(base_work_dir, inference_server_path, model_fname):
    # no internal benchmark to run
    pass
