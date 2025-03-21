import os
import pathlib
import logging

from projects.core.library import env, config, run, configure_logging, export
from projects.matrix_benchmarking.library import visualize

import prepare_llama_cpp, llama_cpp, utils, remote_access, podman_machine, brew, podman, ollama

TESTING_THIS_DIR = pathlib.Path(__file__).absolute().parent
CRC_MAC_AI_SECRET_PATH = pathlib.Path(os.environ.get("CRC_MAC_AI_SECRET_PATH", "/env/CRC_MAC_AI_SECRET_PATH/not_set"))

PREPARE_INFERENCE_SERVERS = dict(
    llama_cpp=prepare_llama_cpp,
    ollama=ollama,
)

INFERENCE_SERVERS = dict(
    llama_cpp=llama_cpp,
    ollama=ollama
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

    brew.install_dependencies(base_work_dir)

    podman_machine.configure_and_start(base_work_dir, force_restart=True)

    prepare_llm_load_test(base_work_dir)

    platforms_to_build_str = config.project.get_config("prepare.platforms.to_build")

    puller_platforms = []
    platforms_to_build = [
        utils.parse_platform(platform_str)
        for platform_str in platforms_to_build_str
    ]

    for platform in platforms_to_build:
        model_puller_str = config.project.get_config(f"prepare.platforms.model_pullers.{platform.inference_server_name}")
        puller_platform = utils.parse_platform(model_puller_str)
        puller_platforms.append(puller_platform)

        if model_puller_str not in platforms_to_build_str:
            platforms_to_build.append(puller_platform)

    platform_binaries = {}
    for platform in platforms_to_build:
        inference_server_config = config.project.get_config(f"prepare.{platform.inference_server_name}", None, print=False)
        if not inference_server_config:
            raise ValueError(f"Cannot prepare the {platform.inference_server_name} inference server: no configuration available :/")

        def prepare_binary():
            # keep only the last binary per platform, on purpose (we
            # only need to save a native platform binary in this
            # prepare step)
            platform_binaries[platform.name] = platform.prepare_inference_server_mod.prepare_binary(base_work_dir, platform)

        run.run_iterable_fields(
            inference_server_config.get("iterable_build_fields"),
            prepare_binary
        )

    # --- #

    models = config.project.get_config("test.model.name")

    platforms_pulled = set()
    for puller_platform in puller_platforms:
        if puller_platform.name in platforms_pulled: continue

        inference_server_binary = platform_binaries[puller_platform.name]
        try:
            puller_platform.inference_server_mod.start_server(base_work_dir, inference_server_binary)
            for model in models if isinstance(models, list) else [models]:
                config.project.set_config("test.model.name", model)

                if puller_platform.inference_server_mod.has_model(base_work_dir, inference_server_binary, model):
                    continue

                puller_platform.inference_server_mod.pull_model(base_work_dir, inference_server_binary, model)

                platforms_pulled.add(puller_platform.name)
        finally:
            puller_platform.inference_server_mod.stop_server(base_work_dir, inference_server_binary)

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

    if not  config.project.get_config("test.llm_load_test.enabled"):
        logging.info(f"llm-load-test not enabled, not preparting it.")
        return

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

    if config.project.get_config("prepare.llm_load_test.install_requirements"):
        remote_access.run_with_ansible_ssh_conf(
            base_work_dir,
            f"{python_bin} -m pip install -r {dest}/requirements.txt --user",
        )
    else:
        logging.info("Not installing llm-load-test requirements.")


def cleanup_models(base_work_dir):
    models = config.project.get_config("test.model.name")
    if not isinstance(models, list):
        models = [models]

    for model in models:
        config.project.set_config("test.model.name", model)
        dest = base_work_dir / utils.model_to_fname(model)
        remote_access.run_with_ansible_ssh_conf(base_work_dir, f"rm -f {dest}")

        # delete from the other inference servers as well

    config.project.set_config("test.model.name", models)
