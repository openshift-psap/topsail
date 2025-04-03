import os
import pathlib
import logging
import tempfile
import json

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
    error_msg = utils.check_expected_platform(platform, system="podman", inference_server_name="ramalama", needs_podman_machine=True, needs_podman=False)
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
    ret = _run(base_work_dir, ramalama_path, "ls --json", check=False, capture_stdout=True)

    if ret.returncode != 0:
        raise ValueError("Ramalama couldn't list the model :/")

    lst = json.loads(ret.stdout)
    for model_info in lst:
        current_model_name = model_info["name"].partition("://")[-1]
        if current_model_name == model_name:
            return True
        if current_model_name == f"{model_name}:latest":
            return True
        logging.info(f"{model_info['name']} != {model_info}")

    return False


def pull_model(base_work_dir, ramalama_path, model_name):
    _run(base_work_dir, ramalama_path, f"pull {model_name} 2>/dev/null")


def start_server(base_work_dir, ramalama_path, stop=False):
    return # nothing to do


def stop_server(base_work_dir, ramalama_path):
    return # nothing to do


def run_model(base_work_dir, platform, ramalama_path, model, unload=False):
    inference_server_port = config.project.get_config("test.inference_server.port")

    artifact_dir_suffix=None
    if unload:
        logging.info("Unloading the model from ramalama server ...")
        artifact_dir_suffix = "_unload"

    want_gpu = platform.want_gpu

    device = config.project.get_config("prepare.podman.container.device") \
        if want_gpu else None

    env_str = " ".join([f"{k}='{v}'" for k, v in _get_env(base_work_dir, ramalama_path).items()])

    run.run_toolbox(
        "mac_ai", "remote_ramalama_run_model",
        base_work_dir=base_work_dir,
        path=ramalama_path,
        name=model,
        unload=unload,
        port=inference_server_port,
        device=device,
        env=env_str,
        mute_stdout=unload,
        artifact_dir_suffix=artifact_dir_suffix,
    )

    return model

def unload_model(base_work_dir, platform, ramalama_path, model):
    run_model(base_work_dir, platform, ramalama_path, model, unload=True)


def run_benchmark(base_work_dir, platform, ramalama_path, model):
    env_str = " ".join([f"{k}='{v}'" for k, v in _get_env(base_work_dir, ramalama_path).items()])

    want_gpu = platform.want_gpu

    device = config.project.get_config("prepare.podman.container.device") \
        if want_gpu else None

    run.run_toolbox(
        "mac_ai", "remote_ramalama_run_bench",
        base_work_dir=base_work_dir,
        path=ramalama_path,
        device=device,
        env=env_str,
        model_name=model,
    )


def _get_env(base_work_dir, ramalama_path):
    return dict(
        PYTHONPATH=ramalama_path.parent.parent,
        RAMALAMA_CONTAINER_ENGINE=podman_mod.get_podman_binary(base_work_dir),
    ) | podman_mod.get_podman_env(base_work_dir)


def _run(base_work_dir, ramalama_path, ramalama_cmd, *, check=False, capture_stdout=False, capture_stderr=False):
    extra_env = _get_env(base_work_dir, ramalama_path)

    return remote_access.run_with_ansible_ssh_conf(
        base_work_dir,
        f"{ramalama_path} {ramalama_cmd}",
        check=check, capture_stdout=capture_stdout, capture_stderr=capture_stderr,
        extra_env=extra_env,
    )


def cleanup_files(base_work_dir):
    dest = base_work_dir / "ramalama-ai"

    if not remote_access.exists(dest):
        logging.info(f"{dest} does not exists, nothing to remove.")
        return

    logging.info(f"Removing {dest} ...")
    remote_access.run_with_ansible_ssh_conf(base_work_dir, f"rm -r {dest}")


def cleanup_models(base_work_dir):
    dest = base_work_dir / ".local/share/ramalama"

    if not remote_access.exists(dest):
        logging.info(f"{dest} does not exists, nothing to remove.")
        return

    logging.info(f"Removing {dest} ...")
    remote_access.run_with_ansible_ssh_conf(base_work_dir, f"rm -r {dest}")
