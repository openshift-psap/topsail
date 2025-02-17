import os
import pathlib
import logging
import tempfile

from projects.core.library import env, config, run, configure_logging, export
from projects.matrix_benchmarking.library import visualize

import podman as podman_mod

def prepare(base_work_dir, use_podman):
    native_system = config.project.get_config("remote_host.system")
    ollama_binaries = {}

    for system in config.project.get_config("prepare.systems"):
        ollama_binaries[system] = prepare_binary(base_work_dir, system, use_podman=False)

    ollama_path = ollama_binaries[native_system]

    model = config.project.get_config("test.model")

    start(base_work_dir, ollama_path)
    try:
        pull_model(base_work_dir, ollama_path, model)
    finally:
        stop(base_work_dir, ollama_path)


def _get_binary_path(base_work_dir, system, use_podman):
    version = config.project.get_config("prepare.ollama.repo.version")
    arch = config.project.get_config("remote_host.arch")

    system_file = config.project.get_config(f"prepare.ollama.repo.{system}.file").replace("{@remote_host.arch}", arch)

    executable = config.project.get_config(f"prepare.ollama.repo.{system}.executable", False, warn=False)
    tarball = config.project.get_config(f"prepare.ollama.repo.{system}.tarball", False, warn=False)

    dest = base_work_dir / f"ollama-{system}-{version}" / system_file

    if executable:
        ollama_path = dest
    else:
        ollama_path = dest.parent / "bin" / "ollama"

    if use_podman:
        ollama_path = f"{podman_mod.get_exec_command_prefix(use_podman)} {ollama_path}"

    return ollama_path, dest, executable, tarball, version


def get_binary_path(base_work_dir, system, use_podman):
    ollama_path, _, _, _, _ = _get_binary_path(base_work_dir, system, use_podman)
    return ollama_path


def prepare_binary(base_work_dir, system, use_podman):
    ollama_path, dest, executable, tarball, version = _get_binary_path(base_work_dir, system, use_podman)
    system_file = dest.name

    source = "/".join([
        config.project.get_config("prepare.ollama.repo.url"),
        "releases/download",
        version,
        system_file
    ])

    if ollama_path.exists():
        logging.info(f"ollama {system} already exists, not downloading it.")
        return ollama_path

    run.run_toolbox(
        "remote", "download",
        source=source, dest=dest,
        executable=executable,
        tarball=tarball,
    )

    return ollama_path


def pull_model(base_work_dir, ollama_path, model):
    run.run_toolbox(
        "mac_ai", "remote_ollama_pull_model",
        base_work_dir=base_work_dir,
        path=ollama_path,
        name=model,
    )


def start(base_work_dir, ollama_path, stop=False):
    artifact_dir_suffix = None
    if stop:
        logging.info("Stopping the ollama server ...")
        artifact_dir_suffix = "_stop"

    run.run_toolbox(
        "mac_ai", "remote_ollama_start",
        base_work_dir=base_work_dir,
        path=ollama_path,
        stop=stop,
        mute_stdout=stop,
        artifact_dir_suffix=artifact_dir_suffix,
    )


def stop(base_work_dir, ollama_path):
    start(base_work_dir, ollama_path, stop=True)


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


def unload_model(base_work_dir, ollama_path, model):
    run_model(base_work_dir, ollama_path, model, unload=True)
