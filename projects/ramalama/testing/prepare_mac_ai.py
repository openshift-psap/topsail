import os
import pathlib
import logging

from projects.core.library import env, config, run, configure_logging, export
from projects.matrix_benchmarking.library import visualize

import utils, remote_access, podman_machine, brew, podman
import ramalama

TESTING_THIS_DIR = pathlib.Path(__file__).absolute().parent
CRC_MAC_AI_SECRET_PATH = pathlib.Path(os.environ.get("CRC_MAC_AI_SECRET_PATH", "/env/CRC_MAC_AI_SECRET_PATH/not_set"))

PREPARE_INFERENCE_SERVERS = dict(
    ramalama=ramalama,
)

INFERENCE_SERVERS = dict(
    ramalama=ramalama,
)


def cleanup():
    base_work_dir = remote_access.prepare()

    # ***

    if config.project.get_config("cleanup.models.ramalama"):
        ramalama.cleanup_models(base_work_dir)

    # ***

    if config.project.get_config("cleanup.files.llm-load-test"):
        cleanup_llm_load_test(base_work_dir)

    if config.project.get_config("cleanup.files.ramalama"):
        ramalama.cleanup_files(base_work_dir)

    # ***

    if config.project.get_config("cleanup.podman_machine.delete"):
        is_running = podman_machine.is_running(base_work_dir)
        if is_running:
            podman_machine.stop(base_work_dir)
        if is_running is not None:
            podman_machine.rm(base_work_dir)
            if config.project.get_config("cleanup.podman_machine.reset"):
                podman_machine.reset(base_work_dir)

    if config.project.get_config("cleanup.files.podman"):
        podman.cleanup(base_work_dir)

    return 0


def prepare():
    base_work_dir = remote_access.prepare()
    if not config.project.get_config("prepare.prepare_only_inference_server"):
        if config.project.get_config("prepare.podman.repo.enabled"):
            podman.prepare_from_gh_binary(base_work_dir)
            podman.prepare_gv_from_gh_binary(base_work_dir)

        brew.install_dependencies(base_work_dir)

        podman_machine.configure_and_start(base_work_dir, force_restart=True)

        prepare_llm_load_test(base_work_dir)

    platform_str = config.project.get_config("test.platform")

    platform = utils.parse_platform(platform_str)

    inference_server_config = config.project.get_config(f"prepare.{platform.inference_server_name}", None, print=False)

    inference_server_binary = platform.prepare_inference_server_mod.prepare_binary(base_work_dir, platform)


    # --- #

    models = config.project.get_config("test.model.name")

    for model in models if isinstance(models, list) else [models]:
        config.project.set_config("test.model.name", model)

        if platform.inference_server_mod.has_model(base_work_dir, inference_server_binary, model):
            continue

        platform.inference_server_mod.pull_model(base_work_dir, inference_server_binary, model)


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
        logging.info("llm-load-test not enabled, not preparing it.")
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
