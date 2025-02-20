import os
import pathlib
import logging
import tempfile

from projects.core.library import env, config, run, configure_logging, export
from projects.matrix_benchmarking.library import visualize

import podman as podman_mod
import remote_access, podman_machine
import hashlib

TESTING_THIS_DIR = pathlib.Path(__file__).absolute().parent

def prepare_test(base_work_dir, use_podman):
    if not use_podman: return

    local_image_name = get_local_image_name(base_work_dir)
    config.project.set_config("prepare.podman.container.image", local_image_name)
    build_from = config.project.get_config("prepare.llama_cpp.repo.'podman/linux'.build_from")
    command = config.project.get_config(f"prepare.llama_cpp.repo.'podman/linux'.{build_from}.command")
    config.project.set_config("prepare.llama_cpp.repo.'podman/linux'.command", command)


def get_local_image_name(base_work_dir):

    FROM = dict(
        desktop_playground=__get_local_image_name_from_desktop_playground,
        local_container_file=__get_local_image_name_from_local_container_file,
    )
    build_from = config.project.get_config("prepare.llama_cpp.repo.'podman/linux'.build_from")
    if build_from not in FROM:
        raise ValueError(f"{build_from} not in {', '.join(FROM.keys())}")

    return FROM[build_from](base_work_dir)


def __get_local_image_name_from_local_container_file(base_work_dir=None):
    def sha256sum(filename):
        with open(filename, 'rb', buffering=0) as f:
            return hashlib.sha256(f.read()).hexdigest()

    container_file = TESTING_THIS_DIR / config.project.get_config("prepare.llama_cpp.repo.'podman/linux'.local_container_file.path")

    tag = sha256sum(container_file)[:8]
    return f"localhost/llama_cpp:{tag}"


def __get_local_image_name_from_desktop_playground(base_work_dir, repo_cfg, only_dest=False):
    repo_cfg = config.project.get_config("prepare.llama_cpp.repo.'podman/linux'.desktop_playground")
    repo_url = repo_cfg["url"]
    dest = base_work_dir / pathlib.Path(repo_url).name

    if only_dest:
        return dest

    image = repo_cfg["image"]
    tag = repo_cfg["tag"]

    if not tag:
        ret = remote_access.run_with_ansible_ssh_conf(
            base_work_dir,
            f"git -C {dest} rev-parse --short HEAD",
            capture_stdout=True,
        )
        tag = ret.stdout.strip()
        config.project.set_config("prepare.llama_cpp.repo.'podman/linux'.tag", tag)

    return f"localhost/{image}:{tag}", dest


def prepare_podman_image(base_work_dir, system="podman/linux"):
    FROM = dict(
        desktop_playground=prepare_podman_image_from_desktop_playground,
        local_container_file=prepare_podman_image_from_local_container_file,
    )
    build_from = config.project.get_config("prepare.llama_cpp.repo.'podman/linux'.build_from")
    if build_from not in FROM:
        raise ValueError(f"{build_from} not in {', '.join(FROM.keys())}")

    return FROM[build_from](base_work_dir, system)


def prepare_podman_image_from_local_container_file(base_work_dir, system="podman/linux"):
    local_image_name = __get_local_image_name_from_local_container_file()
    container_file = TESTING_THIS_DIR / config.project.get_config("prepare.llama_cpp.repo.'podman/linux'.local_container_file.path")

    run.run_toolbox(
        "remote", "build_image",
        podman_cmd=podman_mod.get_podman_binary(),
        base_directory=None,
        prepare_script=None,
        container_file=container_file,
        container_file_is_local=True,
        image=local_image_name,
    )


def prepare_podman_image_from_desktop_playground(base_work_dir, system="podman/linux"):
    repo_cfg = config.project.get_config("prepare.llama_cpp.repo.'podman/linux'.desktop_playground")
    repo_url = repo_cfg["url"]

    # cannot compute the image tag if the repo isn't cloned ...
    dest = __get_local_image_name_from_desktop_playground(base_work_dir, repo_cfg, only_dest=True)

    ref = repo_cfg["ref"]
    run.run_toolbox(
        "remote", "clone",
        repo_url=repo_url, dest=dest, version=ref,
    )

    root_directory = repo_cfg["root_directory"]
    container_file = repo_cfg["container_file"]
    image = repo_cfg["image"]
    tag = repo_cfg["tag"]

    if config.project.get_config("prepare.podman.machine.enabled"):
        podman_machine.configure_and_start(base_work_dir, force_restart=False)

    local_image_name, _ = _get_local_image_name(base_work_dir, repo_cfg)

    run.run_toolbox(
        "remote", "build_image",
        podman_cmd=podman_mod.get_podman_binary(),
        base_directory=dest / root_directory,
        prepare_script=repo_cfg["prepare_script"],
        container_file=container_file,
        image=local_image_name,
    )

    return local_image_name


def prepare_from_gh_binary(base_work_dir, system="darwin"):
    tarball = config.project.get_config(f"prepare.llama_cpp.repo.{system}.tarball")
    if not tarball:
        raise ValueError("llama_cpp on darwin should be a tarball :/")

    use_podman = "podman" in system

    llama_cpp_path, dest, system_file = _get_binary_path(base_work_dir, system, use_podman)

    source = "/".join([
        config.project.get_config("prepare.llama_cpp.repo.url"),
        "releases/download",
        config.project.get_config(f"prepare.llama_cpp.repo.version"),
        system_file,
    ])

    if remote_access.exists(llama_cpp_path):
        logging.info(f"llama_cpp {system} already exists, not downloading it.")
        return llama_cpp_path

    run.run_toolbox(
        "remote", "download",
        source=source,
        dest=dest,
        tarball=tarball,
    )

    return llama_cpp_path


def prepare_binary(base_work_dir, system):
    PREPARE_BY_SYSTEM = {
        "darwin": prepare_from_gh_binary,
        "linux": prepare_from_gh_binary,
        "podman/linux": prepare_podman_image,
    }

    prepare = PREPARE_BY_SYSTEM.get(system)
    if not prepare:
        raise ValueError(f"Invalid system to prepare: {system}. Expected one of {', '.join(PREPARE_BY_SYSTEM)}.")

    return prepare(base_work_dir, system)


def _get_binary_path(base_work_dir, system, use_podman):
    if use_podman:
        podman_prefix = podman_mod.get_exec_command_prefix(use_podman)
        container_command = config.project.get_config(f"prepare.llama_cpp.repo.'podman/linux'.command")
        command = f"{podman_prefix} {container_command}"

        return command, None, None

    version = config.project.get_config(f"prepare.llama_cpp.repo.version")
    arch = config.project.get_config("remote_host.arch")

    file_name = config.project.get_config(f"prepare.llama_cpp.repo.{system}.file")
    system_file = file_name.replace("{@prepare.llama_cpp.repo.version}", version).replace("{@remote_host.arch}", arch)

    dest = base_work_dir / f"llama_cpp-{system}-{version}" / system_file

    llama_cpp_path = dest.parent / "build" / "bin" / "llama-server"

    return llama_cpp_path, dest, system_file


def get_binary_path(base_work_dir, system, use_podman):
    llama_cpp_path, _, _ = _get_binary_path(base_work_dir, system, use_podman)
    return llama_cpp_path


def pull_model(base_work_dir, llama_cpp_path, model):
    inference_server_port = config.project.get_config("test.inference_server.port")
    llama_cpp_path = llama_cpp_path.parent / 'llama-run'

    return run.run_toolbox(
        "mac_ai", "remote_llama_cpp_pull_model",
        base_work_dir=base_work_dir,
        path=llama_cpp_path,
        name=model,
    )


def start(base_work_dir, llama_cpp_path, use_podman=False):
    logging.info("Nothing to do to start the llama_cpp server")


def stop(base_work_dir, llama_cpp_path, use_podman=False):
    logging.info("Nothing to do to stop the llama_cpp server")


def run_model(base_work_dir, llama_cpp_path, model, use_podman=False):
    inference_server_port = config.project.get_config("test.inference_server.port")
    run.run_toolbox(
        "mac_ai", "remote_llama_cpp_run_model",
        base_work_dir=base_work_dir,
        path=llama_cpp_path,
        name=model,
        port=inference_server_port,
    )


def unload_model(base_work_dir, llama_cpp_path, model, use_podman=False):

    if use_podman:
        podman_prefix = podman_mod.get_exec_command_prefix(use_podman)
        command = f"{podman_prefix} pkill python"
    else:
        command = f"pkill llama-server"

    remote_access.run_with_ansible_ssh_conf(
        base_work_dir,
        command,
        check=False,
    )
