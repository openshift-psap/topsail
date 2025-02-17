import os
import pathlib
import logging
import tempfile

from projects.core.library import env, config, run, configure_logging, export

def prepare_binary(base_work_dir, system, podman):
    ollama_path, dest, executable, tarball, version = _get_binary_path(base_work_dir, system, podman)
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
