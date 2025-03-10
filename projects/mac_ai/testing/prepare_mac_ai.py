import os
import pathlib
import logging

from projects.core.library import env, config, run, configure_logging, export
from projects.matrix_benchmarking.library import visualize

import prepare_llama_cpp, llama_cpp, utils, remote_access, podman_machine, brew, podman

TESTING_THIS_DIR = pathlib.Path(__file__).absolute().parent
CRC_MAC_AI_SECRET_PATH = pathlib.Path(os.environ.get("CRC_MAC_AI_SECRET_PATH", "/env/CRC_MAC_AI_SECRET_PATH/not_set"))

PREPARE_INFERENCE_SERVERS = dict(
    llama_cpp=prepare_llama_cpp,
)

INFERENCE_SERVERS = dict(
    llama_cpp=llama_cpp,
)


def cleanup():
    base_work_dir = remote_access.prepare()

    if config.project.get_config(f"cleanup.llm-load-test"):
        cleanup_llm_load_test(base_work_dir)

    if config.project.get_config(f"cleanup.llama_cpp.files"):
        prepare_llama_cpp.cleanup_files(base_work_dir)

    if config.project.get_config(f"cleanup.llama_cpp.image"):
        is_running = podman_machine.is_running(base_work_dir)
        if is_running is None:
            logging.warning("Podman machine doesn't exist.")
        elif not is_running:

            if podman_machine.start(base_work_dir):
                is_running = True
            else:
                logging.warning(f"Could not start podman machine, cannot check/move the {local_image_name} image ...")
                is_running = None

        if is_running:
            prepare_llama_cpp.cleanup_image(base_work_dir)

    if config.project.get_config(f"cleanup.podman_machine.delete"):
        is_running = podman_machine.is_running(base_work_dir)
        if is_running:
            podman_machine.stop(base_work_dir)
        if is_running is not None:
            podman_machine.rm(base_work_dir)
            if config.project.get_config(f"cleanup.podman_machine.reset"):
                podman_machine.reset(base_work_dir)

    if config.project.get_config(f"cleanup.podman"):
        podman.cleanup(base_work_dir)

    if config.project.get_config(f"cleanup.models"):
        cleanup_models(base_work_dir)

    return 0


def prepare():
    base_work_dir = remote_access.prepare()
    if config.project.get_config(f"prepare.podman.repo.enabled", print=False):
        podman.prepare_from_gh_binary(base_work_dir)
        podman.prepare_gv_from_gh_binary(base_work_dir)

    podman_machine.configure_and_start(base_work_dir, force_restart=True)

    prepare_llm_load_test(base_work_dir)
    brew.install_dependencies(base_work_dir)

    inference_server_name = config.project.get_config("test.inference_server.name")
    prepare_inference_server_mod = PREPARE_INFERENCE_SERVERS.get(inference_server_name)
    inference_server_mod = INFERENCE_SERVERS.get(inference_server_name)

    if not (prepare_inference_server_mod and inference_server_mod):
        msg = f"Invalid inference server ({inference_server_name}). Expected one of {', '.join(INFERENCE_SERVERS)}"
        logging.fatal(msg)
        raise ValueError(msg)

    native_platform = config.project.get_config("prepare.native_platform")
    inference_server_binaries = {}

    platforms = config.project.get_config("prepare.platforms")
    # always prepare the native platform
    platforms += [native_platform]

    for platform in set(platforms):
        inference_server_binaries[platform] = prepare_inference_server_mod.prepare_binary(base_work_dir, platform)

    inference_server_native_binary = inference_server_binaries[native_platform]

    model = config.project.get_config("test.model.name")

    model_fname = model_to_fname(model)
    if not remote_access.exists(model_fname):
        inference_server_mod.pull_model(base_work_dir, inference_server_native_binary, model, model_fname)

    if config.project.get_config("prepare.podman.machine.enabled"):
        podman_machine.configure_and_start(base_work_dir, force_restart=False)

    return 0


def cleanup_llm_load_test(base_work_dir):
    dest = base_work_dir / "llm-load-test"

    if not remote_access.exists(dest):
        logging.info(f"{dest} does not exists, nothing to remove.")
        return

    logging.info(f"Removing {dest} ...")
    remote_access.run_with_ansible_ssh_conf(base_work_dir, f"rm -rf {dest}")


def prepare_llm_load_test(base_work_dir):
    dest = base_work_dir / "llm-load-test"

    if remote_access.exists(dest):
        logging.info(f"{dest} already exists, not cloning it.")
        return

    # running this locally to know llm-load-test is configured in TOPSAIL's repo
    submodule_status = run.run("git submodule status | grep llm-load-test", capture_stdout=True).stdout
    submodule_commit = submodule_status.split()[0].replace("+", "")
    submodule_path = submodule_status.split()[1]
    repo_url= run.run(f"git config --file=.gitmodules submodule.'{submodule_path}'.url", capture_stdout=True).stdout.strip()

    run.run_toolbox(
        "remote", "clone",
        repo_url=repo_url, dest=dest, version=submodule_commit,
        artifact_dir_suffix="__llm_load_test",
    )

    python_bin = config.project.get_config("remote_host.python_bin", "python3")

    remote_access.run_with_ansible_ssh_conf(
        base_work_dir,
        f"{python_bin} -m pip install -r {dest}/requirements.txt",
    )


def cleanup_models(base_work_dir):
    models = config.project.get_config("test.model.name")
    if not isinstance(models, list):
        models = [models]

    for model in models:
        dest = base_work_dir / model_to_fname(model)
        remote_access.run_with_ansible_ssh_conf(base_work_dir, f"rm -f {dest}")


def model_to_fname(model):
    model_cache_dir = config.project.get_config("test.model.cache_dir")
    return pathlib.Path(model_cache_dir) / pathlib.Path(model).name
